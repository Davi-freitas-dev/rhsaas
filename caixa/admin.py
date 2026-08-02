from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.urls import path, reverse
from django.utils.html import format_html

from simple_history.admin import SimpleHistoryAdmin
from .forms_dividas import PagamentoParcelaDividaAdminForm
from .forms_pagamentos import (
    escolhas_tipos_custo_servico_pagaveis,
    PagamentoEventoCustoExtraAdminForm,
    PagamentoEventoCustoServicoAdminForm,
)
from .services_dividas import (
    parcelas_disponiveis_para_pagamento,
    prorrogar_parcelas_pendentes,
    recalcular_pagamento_parcelas_por_ids,
)
from .models_pagamentos import (
    PagamentoEventoCustoServico,
    PagamentoEventoCustoExtra,
)
from .permissions import can_approve_budget


class BloquearInclusaoSemSaldoInlineMixin:
    campo_saldo_pendente = "valor_pendente_pagamento"

    def has_add_permission(self, request, obj=None):
        saldo_pendente = getattr(obj, self.campo_saldo_pendente, None)
        if saldo_pendente is not None and saldo_pendente <= 0:
            return False
        return super().has_add_permission(request, obj)


class PagamentoEventoCustoExtraInline(
    BloquearInclusaoSemSaldoInlineMixin,
    admin.TabularInline,
):
    model = PagamentoEventoCustoExtra
    extra = 0
    fields = (
        "descricao",
        "valor_pagamento",
        "data_pagamento",
        "observacao",
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )
    readonly_fields = (
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )


class PagamentoEventoCustoServicoInline(
    BloquearInclusaoSemSaldoInlineMixin,
    admin.TabularInline,
):
    model = PagamentoEventoCustoServico
    extra = 0
    fields = (
        "tipo",
        "descricao",
        "valor_pagamento",
        "data_pagamento",
        "observacao",
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )
    readonly_fields = (
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "valor_pagamento" and formfield:
            formfield.help_text = (
                "Pagamento deve ser maior que zero. Para cancelar um lançamento "
                "incorreto, marque Remover."
        )
        return formfield

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super().get_formset(request, obj, **kwargs)

        class PagamentoCustoServicoInlineFormSet(formset_class):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)
                if not obj:
                    return

                for form in self.forms:
                    self._configurar_tipos_pagaveis(form)

            @property
            def empty_form(self):
                form = super().empty_form
                if obj:
                    self._configurar_tipos_pagaveis(form)
                return form

            def _configurar_tipos_pagaveis(self, form):
                if "tipo" not in form.fields:
                    return
                incluir_tipo = form.instance.tipo if form.instance.pk else None
                form.fields["tipo"].choices = escolhas_tipos_custo_servico_pagaveis(
                    obj,
                    incluir_tipo=incluir_tipo,
                )

        return PagamentoCustoServicoInlineFormSet

from .models import (
    Servico,
    ConfiguracaoFinanceira,
    Cliente,
    Orcamento,
    OrcamentoItem,
    Evento,
    LancamentoFinanceiro,
    ObrigacaoFinanceira,
    BaixaFinanceira,
    BaixaFinanceiraAlocacao,
    ReceitaOperacional,
    DespesaOperacional,
)
from .models_dividas import Credor, DividaFinanceira, ParcelaDivida, PagamentoParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .models_servico import EventoCustoServico
from .models_custo_fixo import (
    AuditoriaCustoRecorrente,
    CustoFixo,
    PlanoCustoRecorrente,
)
from .models_custos_extras import EventoCustoExtra, OrcamentoCustoExtra
from .models_servidores import (
    HistoricoSalarialServidor,
    ParticipacaoServidorEvento,
    Servidor,
    ServidorEventoDiaTrabalhado,
    ServidorServico,
)
from .permissions import (
    VIEW_SERVER_SALARY_PERMISSION,
    VIEW_SERVER_SENSITIVE_DATA_PERMISSION,
)
from .services_cadastros import aprovar_orcamento
from .security_salarios import (
    filtrar_alocacoes_baixa_por_salario,
    filtrar_baixas_por_salario,
    filtrar_custos_fixos_por_salario,
    filtrar_lancamentos_por_salario,
    filtrar_obrigacoes_por_salario,
    usuario_pode_ver_salarios,
)


class AuditoriaAdmin(admin.ModelAdmin):
    readonly_fields = ("criado_em", "atualizado_em", "criado_por", "atualizado_por")

    def save_model(self, request, obj, form, change):
        if not obj.pk and not getattr(obj, "criado_por", None):
            obj.criado_por = request.user

        if hasattr(obj, "atualizado_por"):
            obj.atualizado_por = request.user

        super().save_model(request, obj, form, change)


class AuditoriaFormsetMixin:
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            obj.delete()

        for instance in instances:
            if hasattr(instance, "criado_por") and not instance.pk and not instance.criado_por:
                instance.criado_por = request.user

            if hasattr(instance, "atualizado_por"):
                instance.atualizado_por = request.user

            instance.save()

        formset.save_m2m()


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "codigo",
        "unidade_cobranca",
        "valor_unitario",
        "diaria_padrao",
        "horas_base_diaria",
        "percentual_hora_extra",
        "usa_regra_especial",
        "ativo",
    )
    list_filter = ("usa_regra_especial", "ativo")
    search_fields = ("nome", "codigo")


@admin.register(ConfiguracaoFinanceira)
class ConfiguracaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "valor_alimentacao",
        "valor_transporte",
        "margem_lucro",
        "aliquota_imposto",
        "ativa",
        "data_inicio_vigencia",
    )
    list_filter = ("ativa", "data_inicio_vigencia")
    search_fields = ("nome",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "nome_razao_social",
        "nome_fantasia",
        "tipo_pessoa",
        "cpf_cnpj",
        "telefone",
        "email",
        "ativo",
    )
    list_filter = ("tipo_pessoa", "ativo")
    search_fields = (
        "nome_razao_social",
        "nome_fantasia",
        "cpf_cnpj",
        "telefone",
        "email",
    )


class OrcamentoItemInline(admin.TabularInline):
    model = OrcamentoItem
    extra = 1
    fields = (
        "servico",
        "horas_por_dia",
        "quantidade_dias",
        "quantidade_pessoas",
        "unidade_cobranca_usada",
        "valor_unitario_usado",
        "valor_diaria_usada",
        "horas_base_diaria_usada",
        "percentual_hora_extra_usado",
        "valor_alimentacao_usado",
        "valor_transporte_usado",
        "margem_lucro_usada",
        "aliquota_imposto_usada",
        "valor_dia_por_pessoa",
        "custo_total",
        "valor_imposto",
        "resultado_previsto_item_admin",
        "receita_prevista_item_admin",
    )
    readonly_fields = (
        "valor_dia_por_pessoa",
        "custo_total",
        "valor_imposto",
        "horas_base_diaria_usada",
        "percentual_hora_extra_usado",
        "resultado_previsto_item_admin",
        "receita_prevista_item_admin",
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        labels = {
            "unidade_cobranca_usada": "Unidade de cobranca usada",
            "valor_unitario_usado": "Valor unitario usado",
            "valor_diaria_usada": "Valor da diaria usado",
            "horas_base_diaria_usada": "Horas base da diaria usadas",
            "percentual_hora_extra_usado": "Percentual de hora extra usado",
            "valor_alimentacao_usado": "Valor de alimentacao usado",
            "valor_transporte_usado": "Valor de transporte usado",
            "margem_lucro_usada": "Margem de lucro usada",
            "aliquota_imposto_usada": "Aliquota de imposto usada",
        }
        if db_field.name in labels:
            formfield.label = labels[db_field.name]
        return formfield

    @admin.display(description="Resultado financeiro previsto", ordering="lucro")
    def resultado_previsto_item_admin(self, obj):
        return obj.lucro

    @admin.display(description="Receita prevista", ordering="preco_venda")
    def receita_prevista_item_admin(self, obj):
        return obj.preco_venda


class OrcamentoCustoExtraInline(admin.TabularInline):
    model = OrcamentoCustoExtra
    extra = 1
    fields = (
        "categoria",
        "descricao",
        "valor_previsto",
        "data_vencimento",
        "observacao",
        "evento_custo_extra",
    )
    readonly_fields = ("evento_custo_extra",)


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = (
        "contrato_admin",
        "cliente",
        "nome_evento",
        "data_evento",
        "status",
        "subtotal_custos",
        "total_impostos",
        "resultado_previsto_admin",
        "receita_prevista_admin",
    )
    list_filter = ("status", "data_evento")
    search_fields = (
        "numero",
        "nome_evento",
        "cliente__nome_razao_social",
    )
    inlines = [OrcamentoItemInline, OrcamentoCustoExtraInline]
    actions = ["aprovar_orcamentos_e_gerar_eventos"]
    readonly_fields = (
        "subtotal_custos",
        "total_impostos",
        "total_lucro",
        "total_venda",
        "criado_em",
        "atualizado_em",
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_approve_budget(request.user):
            actions.pop("aprovar_orcamentos_e_gerar_eventos", None)
        return actions

    @admin.display(description="Contrato", ordering="numero")
    def contrato_admin(self, obj):
        return obj.contrato

    @admin.display(description="Receita prevista", ordering="total_venda")
    def receita_prevista_admin(self, obj):
        return obj.total_venda

    @admin.display(description="Resultado financeiro previsto", ordering="total_lucro")
    def resultado_previsto_admin(self, obj):
        return obj.total_lucro

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "numero":
            formfield.label = "Contrato"
        return formfield

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._sincronizar_orcamento_apos_salvar_inlines(form.instance)

    def _sincronizar_orcamento_apos_salvar_inlines(self, orcamento):
        if not orcamento or not orcamento.pk:
            return

        orcamento.recalcular_totais()
        orcamento.refresh_from_db()
        orcamento.sincronizar_evento_aprovado()

    @admin.action(description="Aprovar orçamento(s) e gerar evento(s)")
    def aprovar_orcamentos_e_gerar_eventos(self, request, queryset):
        total_sucesso = 0
        total_erro = 0

        for orcamento in queryset:
            resultado = aprovar_orcamento(orcamento, request.user)
            if resultado["ok"]:
                total_sucesso += 1
            else:
                total_erro += 1
                self.message_user(
                    request,
                    f"Erro no contrato {orcamento.contrato}: {resultado['mensagem']}",
                    level=messages.ERROR
                )

        if total_sucesso:
            self.message_user(
                request,
                f"{total_sucesso} orçamento(s) aprovado(s) e evento(s) gerado(s) com sucesso.",
                level=messages.SUCCESS
            )

        if total_erro:
            self.message_user(
                request,
                f"{total_erro} orçamento(s) não puderam ser processados.",
                level=messages.WARNING
            )


class ReceitaOperacionalInline(admin.TabularInline):
    model = ReceitaOperacional
    extra = 0
    fields = (
        "descricao",
        "valor_previsto",
        "valor_recebido",
        "data_vencimento",
        "data_recebimento",
        "forma_pagamento",
        "baixado_manualmente",
        "motivo_baixa",
        "status",
    )


class DespesaOperacionalInline(admin.TabularInline):
    model = DespesaOperacional
    verbose_name = "Despesa operacional manual"
    verbose_name_plural = "Despesas operacionais manuais"
    extra = 0
    fields = (
        "descricao",
        "categoria",
        "origem",
        "origem_custo_servico_tipo",
        "origem_custo_extra",
        "valor_previsto",
        "valor_pago",
        "data_vencimento",
        "data_pagamento",
        "forma_pagamento",
        "baixado_manualmente",
        "motivo_baixa",
        "status",
    )
    readonly_fields = (
        "origem",
        "origem_custo_servico_tipo",
        "origem_custo_extra",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            origem=DespesaOperacional.ORIGEM_MANUAL,
        )


class EventoCustoExtraInline(admin.TabularInline):
    model = EventoCustoExtra
    extra = 0
    fields = (
        "categoria",
        "descricao",
        "valor_previsto",
        "valor_pago",
        "quitado",
        "motivo_baixa",
        "data_vencimento",
        "observacao",
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )
    readonly_fields = (
        "valor_pago",
        "quitado",
        "motivo_baixa",
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )


@admin.register(Evento)
class EventoAdmin(AuditoriaFormsetMixin, admin.ModelAdmin):
    list_display = (
        "contrato_admin",
        "cliente",
        "nome_evento",
        "data_inicio",
        "data_fim",
        "status",
        "receita_prevista_admin",
        "custo_previsto_admin",
        "resultado_previsto_admin",
        "receita_realizada_admin",
        "custo_realizado_admin",
        "resultado_realizado_admin",
    )
    list_filter = ("status", "data_inicio", "data_fim")
    search_fields = (
        "numero",
        "nome_evento",
        "cliente__nome_razao_social",
        "cliente__nome_fantasia",
        "orcamento__numero",
    )
    inlines = [ReceitaOperacionalInline, DespesaOperacionalInline, EventoCustoExtraInline]
    readonly_fields = (
        "atalhos_financeiros_admin",
        "valor_total_previsto",
        "custo_total_previsto",
        "lucro_previsto",
        "valor_total_realizado",
        "custo_total_realizado",
        "lucro_realizado",
        "criado_em",
        "atualizado_em",
    )

    @admin.display(description="Contrato", ordering="numero")
    def contrato_admin(self, obj):
        return obj.contrato

    @admin.display(description="Receita prevista", ordering="valor_total_previsto")
    def receita_prevista_admin(self, obj):
        return obj.valor_total_previsto

    @admin.display(description="Custo previsto", ordering="custo_total_previsto")
    def custo_previsto_admin(self, obj):
        return obj.custo_total_previsto

    @admin.display(description="Resultado financeiro previsto", ordering="lucro_previsto")
    def resultado_previsto_admin(self, obj):
        return obj.lucro_previsto

    @admin.display(description="Receita realizada", ordering="valor_total_realizado")
    def receita_realizada_admin(self, obj):
        return obj.valor_total_realizado

    @admin.display(description="Custo realizado", ordering="custo_total_realizado")
    def custo_realizado_admin(self, obj):
        return obj.custo_total_realizado

    @admin.display(description="Resultado financeiro realizado", ordering="lucro_realizado")
    def resultado_realizado_admin(self, obj):
        return obj.lucro_realizado

    @admin.display(description="Atalhos financeiros")
    def atalhos_financeiros_admin(self, obj):
        if not obj.pk:
            return "Salve o evento para adicionar custos."

        custo_servico_url = f"{reverse('admin:caixa_eventocustoservico_add')}?evento={obj.pk}"
        custo_extra_url = f"{reverse('admin:caixa_eventocustoextra_add')}?evento={obj.pk}"
        return format_html(
            '<a href="{}">Adicionar custo de serviço</a> &nbsp;|&nbsp; '
            '<a href="{}">Adicionar custo extra</a>',
            custo_servico_url,
            custo_extra_url,
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "numero":
            formfield.label = "Contrato"
        return formfield

    def save_model(self, request, obj, form, change):
        if not change:
            obj._history_user = request.user
            return super().save_model(request, obj, form, change)

        # A edição administrativa do período segue o mesmo lock de Evento da
        # API e das participações; o Admin não pode reabrir a corrida entre
        # intervalo e escala diária.
        from .services_participacoes_servidores import atualizar_evento_com_periodo

        campos = {
            campo: getattr(obj, campo)
            for campo in form.changed_data
            if campo in obj._meta._forward_fields_map
        }
        if campos:
            salvo = atualizar_evento_com_periodo(
                obj,
                valores=campos,
                usuario=request.user,
            )
            for campo in campos:
                setattr(obj, campo, getattr(salvo, campo))

    def has_delete_permission(self, request, obj=None):
        if obj and obj.orcamento_id:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        if obj.orcamento_id:
            messages.warning(
                request,
                (
                    "Eventos gerados por orcamento aprovado nao podem ser "
                    "excluidos fisicamente. Cancele o evento ou ajuste o "
                    "orcamento de origem."
                ),
                fail_silently=True,
            )
            return

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        bloqueados = queryset.filter(orcamento__isnull=False)
        removiveis = queryset.filter(orcamento__isnull=True)

        if bloqueados.exists():
            messages.warning(
                request,
                (
                    "Eventos gerados por orcamento aprovado nao foram removidos. "
                    "Cancele esses eventos ou ajuste o orcamento de origem."
                ),
                fail_silently=True,
            )

        if removiveis.exists():
            super().delete_queryset(request, removiveis)


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "data_lancamento_admin",
        "tipo",
        "fluxo",
        "natureza",
        "valor_lancamento_admin",
        "status",
        "evento",
        "cliente",
    )
    list_filter = (
        "tipo",
        "fluxo",
        "natureza",
        "status",
        "data_lancamento",
    )
    search_fields = (
        "descricao",
        "observacao",
        "evento__numero",
        "evento__nome_evento",
        "cliente__nome_razao_social",
    )
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    @admin.display(description="Data do lançamento", ordering="data_lancamento")
    def data_lancamento_admin(self, obj):
        return obj.data_lancamento

    @admin.display(description="Valor do lançamento", ordering="valor")
    def valor_lancamento_admin(self, obj):
        return obj.valor

    def get_queryset(self, request):
        return filtrar_lancamentos_por_salario(
            super().get_queryset(request),
            request.user,
        )


class BaixaFinanceiraAlocacaoInline(admin.TabularInline):
    model = BaixaFinanceiraAlocacao
    extra = 0
    fields = (
        "obrigacao",
        "valor_alocado",
        "valor_juros",
        "valor_multa",
        "valor_desconto",
        "observacao",
    )

    def get_queryset(self, request):
        return filtrar_alocacoes_baixa_por_salario(
            super().get_queryset(request),
            request.user,
        )


@admin.register(ObrigacaoFinanceira)
class ObrigacaoFinanceiraAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "data_vencimento",
        "tipo",
        "origem",
        "detalhe_origem",
        "descricao",
        "valor_previsto",
        "valor_realizado",
        "valor_pendente",
        "status",
        "evento",
        "cliente",
    )
    list_filter = (
        "tipo",
        "origem",
        "fluxo",
        "natureza",
        "status",
        "data_vencimento",
    )
    search_fields = (
        "chave_origem",
        "descricao",
        "referencia",
        "evento__numero",
        "evento__nome_evento",
        "cliente__nome_razao_social",
    )
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    def get_queryset(self, request):
        return filtrar_obrigacoes_por_salario(
            super().get_queryset(request),
            request.user,
        )


@admin.register(BaixaFinanceira)
class BaixaFinanceiraAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    inlines = [BaixaFinanceiraAlocacaoInline]
    list_display = (
        "data_baixa",
        "tipo",
        "fluxo",
        "natureza",
        "valor_baixa_admin",
        "status",
        "fonte_escrita",
        "evento",
        "cliente",
    )
    list_filter = (
        "tipo",
        "fluxo",
        "natureza",
        "status",
        "fonte_escrita",
        "data_baixa",
    )
    search_fields = (
        "chave_origem",
        "descricao",
        "observacao",
        "evento__numero",
        "evento__nome_evento",
        "cliente__nome_razao_social",
    )

    @admin.display(description="Valor da baixa", ordering="valor_total")
    def valor_baixa_admin(self, obj):
        return obj.valor_total
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    def get_queryset(self, request):
        return filtrar_baixas_por_salario(
            super().get_queryset(request),
            request.user,
        )


@admin.register(BaixaFinanceiraAlocacao)
class BaixaFinanceiraAlocacaoAdmin(admin.ModelAdmin):
    list_display = (
        "baixa",
        "obrigacao",
        "valor_alocado",
        "valor_juros",
        "valor_multa",
        "valor_desconto",
    )
    search_fields = (
        "baixa__descricao",
        "obrigacao__descricao",
        "obrigacao__chave_origem",
    )
    readonly_fields = ("criado_em", "atualizado_em")

    def get_queryset(self, request):
        return filtrar_alocacoes_baixa_por_salario(
            super().get_queryset(request),
            request.user,
        )


@admin.register(ReceitaOperacional)
class ReceitaOperacionalAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "evento",
        "cliente",
        "descricao",
        "valor_previsto",
        "valor_recebido",
        "valor_pendente_recebimento_admin",
        "data_vencimento",
        "data_recebimento",
        "forma_pagamento",
        "baixado_manualmente",
        "status",
    )

    readonly_fields = (
        "valor_pendente_recebimento_admin",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    fieldsets = (
        ("Dados principais", {
            "fields": (
                "evento",
                "cliente",
                "descricao",
                "valor_previsto",
                "valor_recebido",
                "valor_pendente_recebimento_admin",
                "data_vencimento",
                "data_recebimento",
                "forma_pagamento",
                "baixado_manualmente",
                "motivo_baixa",
                "status",
            )
        }),
        ("Auditoria", {
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    @admin.display(description="Valor pendente a receber", ordering="valor_previsto")
    def valor_pendente_recebimento_admin(self, obj):
        return obj.valor_pendente_recebimento

    list_filter = (
        "status",
        "baixado_manualmente",
        "forma_pagamento",
        "data_vencimento",
        "data_recebimento",
    )
    search_fields = (
        "descricao",
        "evento__numero",
        "evento__nome_evento",
        "cliente__nome_razao_social",
        "cliente__nome_fantasia",
    )


@admin.register(DespesaOperacional)
class DespesaOperacionalAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    CAMPOS_ORIGEM_SINCRONIZADA_READONLY = (
        "evento",
        "descricao",
        "categoria",
        "valor_previsto",
        "valor_pago",
        "data_vencimento",
        "data_pagamento",
        "forma_pagamento",
        "baixado_manualmente",
        "motivo_baixa",
        "status",
    )

    list_display = (
        "evento",
        "descricao",
        "categoria",
        "origem_pagamento_admin",
        "valor_previsto",
        "valor_pago",
        "valor_pendente_pagamento_admin",
        "data_vencimento",
        "data_pagamento",
        "forma_pagamento",
        "baixado_manualmente",
        "status",
    )

    readonly_fields = (
        "valor_pendente_pagamento_admin",
        "origem_pagamento_admin",
        "origem",
        "origem_custo_servico_tipo",
        "origem_custo_extra",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    fieldsets = (
        ("Dados principais", {
            "fields": (
                "evento",
                "descricao",
                "categoria",
                "origem_pagamento_admin",
                "origem",
                "origem_custo_servico_tipo",
                "origem_custo_extra",
                "valor_previsto",
                "valor_pago",
                "valor_pendente_pagamento_admin",
                "data_vencimento",
                "data_pagamento",
                "forma_pagamento",
                "baixado_manualmente",
                "motivo_baixa",
                "status",
            )
        }),
        ("Auditoria", {
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    @admin.display(description="Valor pendente a pagar", ordering="valor_previsto")
    def valor_pendente_pagamento_admin(self, obj):
        return obj.valor_pendente_pagamento

    @admin.display(description="Origem", ordering="origem")
    def origem_pagamento_admin(self, obj):
        return obj.origem_pagamento_display

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.origem != DespesaOperacional.ORIGEM_MANUAL:
            readonly_fields.extend(self.CAMPOS_ORIGEM_SINCRONIZADA_READONLY)
        return tuple(dict.fromkeys(readonly_fields))

    list_filter = (
        "categoria",
        "origem",
        "status",
        "baixado_manualmente",
        "forma_pagamento",
        "data_vencimento",
        "data_pagamento",
    )
    search_fields = (
        "descricao",
        "evento__numero",
        "evento__nome_evento",
        "evento__cliente__nome_razao_social",
    )


@admin.register(Investimento)
class InvestimentoAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "descricao",
        "categoria",
        "tipo_fluxo",
        "valor_previsto",
        "valor_realizado",
        "data_prevista",
        "evento",
        "baixado_manualmente",
        "status",
        "ativo",
    )
    list_filter = (
        "categoria",
        "tipo_fluxo",
        "status",
        "evento",
        "baixado_manualmente",
        "ativo",
    )
    search_fields = (
        "descricao",
        "observacao",
        "evento__numero",
        "evento__nome_evento",
    )
    ordering = ("-data_prevista", "-id")


@admin.register(FinanciamentoMovimentacao)
class FinanciamentoMovimentacaoAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    CAMPOS_ENTRADA_AUTOMATICA_READONLY = (
        "descricao",
        "categoria",
        "tipo_fluxo",
        "valor_previsto",
        "valor_realizado",
        "data_prevista",
        "data_realizacao",
        "evento",
        "status",
        "ativo",
        "observacao",
    )

    list_display = (
        "descricao",
        "categoria",
        "tipo_fluxo",
        "valor_previsto",
        "valor_realizado",
        "data_prevista",
        "evento",
        "origem_divida_admin",
        "status",
        "ativo",
    )

    readonly_fields = (
        "divida_financeira",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    fieldsets = (
        ("Dados principais", {
            "fields": (
                "descricao",
                "categoria",
                "tipo_fluxo",
                "valor_previsto",
                "valor_realizado",
                "data_prevista",
                "data_realizacao",
                "evento",
                "divida_financeira",
                "status",
                "ativo",
            )
        }),
        ("Observacoes", {
            "fields": ("observacao",)
        }),
        ("Auditoria", {
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    list_filter = (
        "categoria",
        "tipo_fluxo",
        "status",
        "evento",
        "ativo",
    )
    search_fields = (
        "descricao",
        "observacao",
        "evento__numero",
        "evento__nome_evento",
        "divida_financeira__credor",
        "divida_financeira__descricao",
    )
    ordering = ("-data_prevista", "-id")

    @admin.display(description="Origem da entrada")
    def origem_divida_admin(self, obj):
        if obj.divida_financeira_id:
            return "Divida financeira"
        return "Movimentacao manual"

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.divida_financeira_id:
            readonly_fields.extend(self.CAMPOS_ENTRADA_AUTOMATICA_READONLY)
        return tuple(dict.fromkeys(readonly_fields))

    def has_delete_permission(self, request, obj=None):
        if obj and obj.divida_financeira_id:
            return False
        return super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        automaticas = queryset.filter(divida_financeira__isnull=False)
        manuais = queryset.filter(divida_financeira__isnull=True)

        if automaticas.exists():
            messages.warning(
                request,
                (
                    "Entradas FCF automaticas de dividas financeiras nao foram "
                    "removidas. Edite ou remova a divida de origem."
                ),
                fail_silently=True,
            )

        if manuais.exists():
            super().delete_queryset(request, manuais)


@admin.register(EventoCustoServico)
class EventoCustoServicoAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "evento",
        "servico",
        "valor_diarias",
        "valor_alimentacao",
        "valor_transporte",
        "diarias_quitadas",
        "alimentacao_quitada",
        "transporte_quitado",
        "motivo_baixa",
        "total_pago_geral",
    )
    readonly_fields = (
        "total_pago_diarias",
        "total_pago_alimentacao",
        "total_pago_transporte",
        "total_pago_geral",
        "valor_pendente_diarias",
        "valor_pendente_alimentacao",
        "valor_pendente_transporte",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )
    fieldsets = (
        ("Dados principais", {
            "fields": (
                "evento",
                "servico",
                "valor_diarias",
                "valor_alimentacao",
                "valor_transporte",
                "diarias_quitadas",
                "alimentacao_quitada",
                "transporte_quitado",
                "motivo_baixa",
                "observacao",
            )
        }),
        ("Realizado", {
            "fields": (
                "total_pago_diarias",
                "valor_pendente_diarias",
                "total_pago_alimentacao",
                "valor_pendente_alimentacao",
                "total_pago_transporte",
                "valor_pendente_transporte",
                "total_pago_geral",
            )
        }),
        ("Auditoria", {
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )
    list_filter = (
        "servico",
        "diarias_quitadas",
        "alimentacao_quitada",
        "transporte_quitado",
        "evento__status",
    )
    search_fields = ("evento__numero", "evento__nome_evento", "servico__nome")
    inlines = [PagamentoEventoCustoServicoInline]

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            campos.extend(("evento", "servico"))
        return tuple(dict.fromkeys(campos))

    def delete_model(self, request, obj):
        # `EventoCustoServico.delete()` aplica o lock de Evento e bloqueia a
        # remoção de uma fonte ainda usada no rateio.
        obj._history_user = request.user
        obj.delete()

    def delete_queryset(self, request, queryset):
        # O bulk delete padrão contorna Model.delete(); processar cada custo
        # preserva a mesma regra transacional da API e do orçamento. A
        # transação externa garante que uma fonte protegida encontrada no
        # meio da seleção reverta as exclusões anteriores.
        with transaction.atomic():
            for obj in queryset.order_by("evento_id", "servico_id", "pk"):
                obj._history_user = request.user
                obj.delete()
@admin.register(PagamentoEventoCustoServico)
class PagamentoEventoCustoServicoAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    form = PagamentoEventoCustoServicoAdminForm
    list_display = (
        "custo_servico",
        "tipo",
        "valor_pago_admin",
        "data_pagamento",
    )
    list_filter = ("tipo", "data_pagamento")
    search_fields = (
        "custo_servico__evento__nome_evento",
        "custo_servico__evento__numero",
        "custo_servico__servico__nome",
        "descricao",
    )

    @admin.display(description="Valor pago", ordering="valor_pagamento")
    def valor_pago_admin(self, obj):
        return obj.valor_pagamento


@admin.register(PagamentoEventoCustoExtra)
class PagamentoEventoCustoExtraAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    form = PagamentoEventoCustoExtraAdminForm
    list_display = (
        "custo_extra",
        "valor_pago_admin",
        "data_pagamento",
    )
    list_filter = ("data_pagamento",)
    search_fields = (
        "custo_extra__evento__nome_evento",
        "custo_extra__evento__numero",
        "custo_extra__descricao",
        "descricao",
    )

    @admin.display(description="Valor pago", ordering="valor_pagamento")
    def valor_pago_admin(self, obj):
        return obj.valor_pagamento

@admin.register(EventoCustoExtra)
class EventoCustoExtraAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "evento",
        "categoria",
        "descricao",
        "valor_previsto",
        "quitado",
        "total_pago",
        "valor_pendente_pagamento_admin",
        "data_vencimento",
    )
    readonly_fields = (
        "valor_pago",
        "quitado",
        "motivo_baixa",
        "total_pago",
        "valor_pendente_pagamento_admin",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )
    fieldsets = (
        ("Dados principais", {
            "fields": (
                "evento",
                "categoria",
                "descricao",
                "valor_previsto",
                "valor_pago",
                "quitado",
                "motivo_baixa",
                "total_pago",
                "valor_pendente_pagamento_admin",
                "data_vencimento",
                "observacao",
            )
        }),
        ("Auditoria", {
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )
    list_filter = ("categoria", "quitado", "data_vencimento", "evento__status")
    search_fields = (
        "descricao",
        "evento__numero",
        "evento__nome_evento",
        "evento__cliente__nome_razao_social",
    )
    inlines = [PagamentoEventoCustoExtraInline]

    @admin.display(description="Valor pendente a pagar", ordering="valor_previsto")
    def valor_pendente_pagamento_admin(self, obj):
        return obj.valor_pendente_pagamento


class ParcelaDividaInline(admin.TabularInline):
    model = ParcelaDivida
    extra = 0
    readonly_fields = (
        "numero_parcela",
        "data_vencimento_original",
        "data_vencimento_atual",
        "valor_principal",
        "valor_juros",
        "valor_multa",
        "valor_desconto",
        "valor_pago",
        "status",
        "criado_em",
        "atualizado_em",
    )
    can_delete = False


class DividaFinanceiraAdminForm(forms.ModelForm):
    class Meta:
        model = DividaFinanceira
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "credor_cadastro" in self.fields:
            self.fields["credor_cadastro"].required = True
            self.fields["credor_cadastro"].help_text = (
                "Selecione um credor ativo ja cadastrado. "
                "Cadastre novos credores na tela Credores."
            )
            credores = Credor.objects.filter(ativo=True)
            credor_atual_id = getattr(self.instance, "credor_cadastro_id", None)

            if credor_atual_id:
                credores = Credor.objects.filter(
                    Q(ativo=True) | Q(pk=credor_atual_id)
                )

            self.fields["credor_cadastro"].queryset = credores.order_by("nome", "id")

    def clean(self):
        dados = super().clean()
        credor = dados.get("credor_cadastro")

        if credor:
            dados["credor"] = credor.nome
            self.instance.credor = credor.nome

        return dados


@admin.register(Credor)
class CredorAdmin(AuditoriaAdmin):
    list_display = ("nome", "documento", "ativo", "atualizado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "documento")
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )
    fieldsets = (
        ("Dados principais", {
            "fields": (
                "nome",
                "documento",
                "ativo",
            )
        }),
        ("Observacoes", {
            "fields": ("observacao",)
        }),
        ("Auditoria", {
            "classes": ("collapse",),
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        if (
            request.GET.get("app_label") == "caixa"
            and request.GET.get("model_name") == "dividafinanceira"
            and request.GET.get("field_name") == "credor_cadastro"
        ):
            queryset = queryset.filter(ativo=True)

        return queryset, use_distinct


@admin.register(DividaFinanceira)
class DividaFinanceiraAdmin(AuditoriaAdmin):
    form = DividaFinanceiraAdminForm
    list_display = (
        "credor",
        "descricao",
        "tipo",
        "evento",
        "valor_contratado",
        "quantidade_parcelas",
        "status",
        "data_contratacao",
    )
    list_filter = ("tipo", "status", "evento")
    autocomplete_fields = ("credor_cadastro",)
    search_fields = (
        "credor_cadastro__nome",
        "credor_cadastro__documento",
        "credor",
        "descricao",
        "evento__numero",
        "evento__nome_evento",
    )
    readonly_fields = (
        "credor",
        "valor_a_pagar_calculado_admin",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )
    inlines = [ParcelaDividaInline]

    fieldsets = (
        ("Dados principais", {
            "fields": (
                "descricao",
                "credor_cadastro",
                "tipo",
                "status",
            )
        }),
        ("Condições da dívida", {
            "fields": (
                "data_contratacao",
                "valor_contratado",
                "taxa_juros_mensal",
                "quantidade_parcelas",
                "dia_vencimento",
                "valor_a_pagar_calculado_admin",
            )
        }),
        ("Dimensao operacional", {
            "fields": (
                "evento",
            )
        }),
        ("Observações", {
            "fields": ("observacao",)
        }),
        ("Auditoria", {
            "classes": ("collapse",),
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    @admin.display(description="Valor ainda devido (calculado)")
    def valor_a_pagar_calculado_admin(self, obj):
        return obj.saldo_devedor

    def save_model(self, request, obj, form, change):
        campos_parcelas_contratadas = {
            "valor_contratado",
            "quantidade_parcelas",
            "dia_vencimento",
        }
        sincronizar_parcelas = change and bool(
            campos_parcelas_contratadas.intersection(
                getattr(form, "changed_data", [])
            )
        )

        with transaction.atomic():
            super().save_model(request, obj, form, change)

            if sincronizar_parcelas:
                obj.sincronizar_parcelas_contratadas(usuario=request.user)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if not change and not form.instance.parcelas.exists():
            form.instance.gerar_parcelas_iniciais()


@admin.action(description="Prorrogar parcela para o mês seguinte")
def prorrogar_parcelas(modeladmin, request, queryset):
    quantidade = prorrogar_parcelas_pendentes(queryset, request.user)

    modeladmin.message_user(
        request,
        f"{quantidade} parcela(s) prorrogada(s) com sucesso.",
        level=messages.SUCCESS
    )


class PagamentoParcelaDividaInline(
    BloquearInclusaoSemSaldoInlineMixin,
    admin.TabularInline,
):
    model = PagamentoParcelaDivida
    extra = 0
    fields = (
        "data_pagamento",
        "valor_pagamento",
        "forma_pagamento",
        "observacao",
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )
    readonly_fields = (
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )


@admin.register(ParcelaDivida)
class ParcelaDividaAdmin(AuditoriaFormsetMixin, AuditoriaAdmin):
    list_display = (
        "divida",
        "evento_admin",
        "numero_parcela",
        "data_vencimento_atual",
        "valor_total_devido",
        "valor_pago",
        "contas_pendentes_admin",
        "baixado_manualmente",
        "status",
    )
    list_filter = (
        "status",
        "baixado_manualmente",
        "divida__tipo",
        "divida__evento",
    )
    search_fields = (
        "divida__descricao",
        "divida__credor",
        "divida__evento__numero",
        "divida__evento__nome_evento",
    )
    readonly_fields = (
        "valor_total_devido",
        "valor_pago",
        "contas_pendentes_admin",
        "baixado_manualmente",
        "motivo_baixa",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )
    actions = [prorrogar_parcelas]
    inlines = [PagamentoParcelaDividaInline]

    fieldsets = (
        ("Dados da parcela", {
            "fields": (
                "divida",
                "numero_parcela",
                "status",
                "parcela_origem",
            )
        }),
        ("Vencimentos", {
            "fields": (
                "data_vencimento_original",
                "data_vencimento_atual",
            )
        }),
        ("Valores", {
            "fields": (
                "valor_principal",
                "valor_juros",
                "valor_multa",
                "valor_desconto",
                "valor_total_devido",
                "valor_pago",
                "contas_pendentes_admin",
                "baixado_manualmente",
                "motivo_baixa",
            )
        }),
        ("Observações", {
            "fields": ("observacao",)
        }),
        ("Auditoria", {
            "classes": ("collapse",),
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    @admin.display(description="Evento", ordering="divida__evento__numero")
    def evento_admin(self, obj):
        return obj.divida.evento or "-"

    @admin.display(description="Contas pendentes", ordering="valor_principal")
    def contas_pendentes_admin(self, obj):
        return obj.valor_pendente_pagamento


@admin.register(PagamentoParcelaDivida)
class PagamentoParcelaDividaAdmin(AuditoriaAdmin):
    form = PagamentoParcelaDividaAdminForm

    list_display = (
        "parcela",
        "evento_admin",
        "data_pagamento",
        "valor_pago_admin",
        "forma_pagamento",
        "criado_por",
    )
    list_filter = (
        "forma_pagamento",
        "data_pagamento",
        "parcela__divida__evento",
    )
    search_fields = (
        "parcela__divida__descricao",
        "parcela__divida__credor",
        "parcela__divida__evento__numero",
        "parcela__divida__evento__nome_evento",
    )
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    fieldsets = (
        ("Seleção", {
            "fields": (
                "divida",
                "parcela",
            )
        }),
        ("Pagamento", {
            "fields": (
                "data_pagamento",
                "valor_pagamento",
                "forma_pagamento",
                "observacao",
            )
        }),
        ("Auditoria", {
            "classes": ("collapse",),
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    @admin.display(description="Evento", ordering="parcela__divida__evento__numero")
    def evento_admin(self, obj):
        return obj.parcela.divida.evento or "-"

    @admin.display(description="Valor pago", ordering="valor_pagamento")
    def valor_pago_admin(self, obj):
        return obj.valor_pagamento

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "parcelas-por-divida/",
                self.admin_site.admin_view(self.parcelas_por_divida_view),
                name="caixa_pagamentoparceladivida_parcelas_por_divida",
            ),
        ]
        return custom_urls + urls

    def parcelas_por_divida_view(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        divida_id = request.GET.get("divida_id")

        if not divida_id:
            return JsonResponse({"parcelas": []})

        parcelas = parcelas_disponiveis_para_pagamento(divida_id)

        data = [
            {
                "id": parcela.id,
                "texto": (
                    f"Parcela {parcela.rotulo_parcela} - "
                    f"Vencimento: {parcela.data_vencimento_atual:%d/%m/%Y} - "
                    f"Contas pendentes: {parcela.valor_pendente_pagamento}"
                ),
                "installmentLabel": parcela.rotulo_parcela,
                "dueDate": parcela.data_vencimento_atual.isoformat(),
                "pendingPaymentAmount": str(parcela.valor_pendente_pagamento),
                "pendingAccountsAmount": str(parcela.valor_pendente_pagamento),
                "valor_pendente_pagamento": str(parcela.valor_pendente_pagamento),
                "saldo_em_aberto": str(parcela.saldo_em_aberto),
            }
            for parcela in parcelas
        ]

        return JsonResponse({"parcelas": data})

    def delete_model(self, request, obj):
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        parcelas_ids = list(
            queryset.values_list("parcela_id", flat=True).distinct()
        )

        super().delete_queryset(request, queryset)

        recalcular_pagamento_parcelas_por_ids(parcelas_ids)


@admin.register(CustoFixo)
class CustoFixoAdmin(AuditoriaAdmin):
    list_display = (
        "descricao",
        "categoria",
        "valor_previsto",
        "valor_pago",
        "valor_pendente_pagamento_admin",
        "data_vencimento",
        "data_pagamento",
        "baixado_manualmente",
        "status",
        "recorrente",
        "quantidade_meses",
        "gerado_automaticamente",
        "ativo",
    )
    list_filter = (
        "categoria",
        "status",
        "baixado_manualmente",
        "ativo",
        "recorrente",
        "gerado_automaticamente",
        "data_vencimento",
    )
    search_fields = ("descricao", "observacao")
    readonly_fields = (
        "valor_pendente_pagamento_admin",
        "gerado_automaticamente",
        "custo_pai",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    fieldsets = (
        ("Dados principais", {
            "fields": (
                "descricao",
                "categoria",
                "valor_previsto",
                "valor_pago",
                "valor_pendente_pagamento_admin",
                "data_vencimento",
                "data_pagamento",
                "baixado_manualmente",
                "motivo_baixa",
                "status",
                "observacao",
                "ativo",
            )
        }),
        ("Recorrência", {
            "fields": (
                "recorrente",
                "quantidade_meses",
                "gerado_automaticamente",
                "custo_pai",
            )
        }),
        ("Auditoria", {
            "classes": ("collapse",),
            "fields": (
                "criado_em",
                "atualizado_em",
                "criado_por",
                "atualizado_por",
            )
        }),
    )

    @admin.display(description="Valor pendente a pagar", ordering="valor_previsto")
    def valor_pendente_pagamento_admin(self, obj):
        return obj.valor_pendente_pagamento

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return filtrar_custos_fixos_por_salario(
            super().get_queryset(request),
            request.user,
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is None:
            readonly.extend(["recorrente", "quantidade_meses"])
        if obj and (
            obj.plano_recorrente_id
            or obj.origem_recorrencia in {"plano", "salario"}
        ):
            readonly.extend(campo.name for campo in self.model._meta.fields)
        return tuple(dict.fromkeys(readonly))

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        if obj.plano_recorrente_id or obj.origem_recorrencia == "salario":
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PlanoCustoRecorrente)
class PlanoCustoRecorrenteAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "descricao",
        "origem",
        "categoria",
        "data_inicio",
        "data_fim",
        "dia_vencimento",
        "data_autorizacao_materializacao",
        "ativo",
    )
    list_filter = ("origem", "categoria", "ativo", "data_inicio", "data_fim")
    search_fields = ("descricao", "observacao", "servidor__nome")
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not usuario_pode_ver_salarios(request.user):
            queryset = queryset.exclude(origem=PlanoCustoRecorrente.ORIGEM_SALARIO)
        return queryset

    def get_readonly_fields(self, request, obj=None):
        return tuple(campo.name for campo in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ServidorServicoInline(admin.TabularInline):
    model = ServidorServico
    extra = 0
    can_delete = False
    fields = (
        "servico",
        "ativo",
        "criado_por",
        "atualizado_por",
        "criado_em",
        "atualizado_em",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Servidor)
class ServidorAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = (
        "nome",
        "tipo_documento",
        "documento_mascarado_admin",
        "tipo_vinculo",
        "ativo",
        "atualizado_em",
    )
    list_filter = ("ativo", "tipo_vinculo", "tipo_documento")
    search_fields = ("nome", "documento", "email", "telefone")
    inlines = (ServidorServicoInline,)
    readonly_fields = (
        "tipo_vinculo",
        "salario_mensal",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)

    def get_fields(self, request, obj=None):
        campos = [campo.name for campo in self.model._meta.fields]
        if not request.user.has_perm(VIEW_SERVER_SENSITIVE_DATA_PERMISSION):
            campos = [
                campo
                for campo in campos
                if campo
                not in {
                    "documento",
                    "telefone",
                    "email",
                    "data_nascimento",
                    "endereco",
                    "observacoes",
                }
            ]
        if not request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION):
            campos = [
                campo
                for campo in campos
                if campo
                not in {
                    "salario_mensal",
                    "data_inicio_contrato",
                    "data_fim_contrato",
                    "dia_pagamento_salario",
                    "data_autorizacao_custo_salarial",
                }
            ]
        return tuple(campos)

    def get_exclude(self, request, obj=None):
        return ()

    def get_search_fields(self, request):
        if request.user.has_perm(VIEW_SERVER_SENSITIVE_DATA_PERMISSION):
            return self.search_fields
        return ("nome",)

    def history_view(self, request, object_id, extra_context=None):
        if not (
            request.user.has_perm(VIEW_SERVER_SENSITIVE_DATA_PERMISSION)
            and request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION)
        ):
            raise PermissionDenied
        return super().history_view(request, object_id, extra_context)

    @admin.display(description="Documento")
    def documento_mascarado_admin(self, obj):
        return obj.documento_mascarado


@admin.register(ServidorServico)
class ServidorServicoAdmin(SimpleHistoryAdmin, AuditoriaAdmin):
    list_display = ("servidor", "servico", "ativo", "criado_em")
    list_filter = ("ativo", "servico")
    search_fields = ("servidor__nome", "servico__nome")
    readonly_fields = (
        "servidor",
        "servico",
        "ativo",
        "criado_em",
        "atualizado_em",
        "criado_por",
        "atualizado_por",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HistoricoSalarialServidor)
class HistoricoSalarialServidorAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ("servidor_nome_snapshot", "valor", "data_inicio", "data_fim")
    list_filter = ("data_inicio", "data_fim")
    search_fields = ("servidor_nome_snapshot", "servidor__nome")
    readonly_fields = [
        campo.name for campo in HistoricoSalarialServidor._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ParticipacaoServidorEvento)
class ParticipacaoServidorEventoAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = (
        "servidor_nome_exibicao",
        "evento",
        "servico_nome_snapshot",
        "tipo_vinculo",
        "valor_calculado",
        "valor_final",
        "valor_editado_manualmente",
    )
    list_filter = (
        "tipo_vinculo",
        "valor_editado_manualmente",
        "evento__status",
        "servico",
    )
    search_fields = (
        "servidor_nome_snapshot",
        "servico_nome_snapshot",
        "evento__numero",
        "evento__nome_evento",
    )
    readonly_fields = [
        campo.name for campo in ParticipacaoServidorEvento._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Toda mutação de participação precisa passar pelo serviço transacional
        # (escala, rateio, locks, Demo policy e auditoria). O Admin é somente
        # leitura para não abrir um atalho que contorne essas invariantes.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def get_exclude(self, request, obj=None):
        campos = list(super().get_exclude(request, obj) or [])
        if not request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION):
            campos.append("salario_mensal_referencia")
        if not request.user.has_perm(VIEW_SERVER_SENSITIVE_DATA_PERMISSION):
            campos.append("servidor_identificador_snapshot")
        return campos


@admin.register(ServidorEventoDiaTrabalhado)
class ServidorEventoDiaTrabalhadoAdmin(admin.ModelAdmin):
    list_display = (
        "participacao",
        "data",
        "quantidade_horas",
        "criado_em",
        "atualizado_em",
    )
    list_filter = ("data", "participacao__evento__status")
    search_fields = (
        "participacao__servidor_nome_snapshot",
        "participacao__evento__numero",
        "participacao__evento__nome_evento",
        "participacao__servico_nome_snapshot",
    )
    readonly_fields = [
        campo.name for campo in ServidorEventoDiaTrabalhado._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditoriaCustoRecorrente)
class AuditoriaCustoRecorrenteAdmin(admin.ModelAdmin):
    list_display = (
        "identificador_tecnico",
        "tipo_evento",
        "origem",
        "plano_id",
        "competencia",
        "status",
        "codigo_motivo",
        "occurrences_count",
        "last_occurred_at",
    )
    list_filter = (
        "tipo_evento",
        "origem",
        "status",
        "codigo_motivo",
    )
    search_fields = (
        "identificador_tecnico",
        "correlation_id",
    )
    readonly_fields = tuple(
        campo.name for campo in AuditoriaCustoRecorrente._meta.fields
    )

    @staticmethod
    def _pode_ver(request):
        return request.user.has_perm(
            "caixa.view_auditoria_custos_recorrentes"
        )

    def has_module_permission(self, request):
        return self._pode_ver(request)

    def has_view_permission(self, request, obj=None):
        return self._pode_ver(request)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        if not self._pode_ver(request):
            return super().get_queryset(request).none()
        return super().get_queryset(request)
