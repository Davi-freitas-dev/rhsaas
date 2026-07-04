document.addEventListener("DOMContentLoaded", function () {
  const dividaField = document.getElementById("id_divida");
  const parcelaField = document.getElementById("id_parcela");
  const valorPagamentoField = document.getElementById("id_valor_pagamento");

  if (!dividaField || !parcelaField || !valorPagamentoField) {
    return;
  }

  let ultimoRequestId = 0;

  function criarOpcaoVazia(texto = "---------") {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = texto;
    return option;
  }

  function limparParcelas(texto = "---------") {
    parcelaField.innerHTML = "";
    parcelaField.appendChild(criarOpcaoVazia(texto));
  }

  function setLoadingParcelas() {
    limparParcelas("Carregando parcelas...");
  }

  function preencherParcelas(parcelas) {
    limparParcelas();

    parcelas.forEach(function (parcela) {
      const option = document.createElement("option");
      option.value = parcela.id;
      option.textContent = parcela.texto;
      option.dataset.valorPendentePagamento =
        parcela.pendingPaymentAmount ||
        parcela.valor_pendente_pagamento ||
        parcela.saldo_em_aberto;
      parcelaField.appendChild(option);
    });

    if (!parcelas.length) {
      limparParcelas("Nenhuma parcela disponível");
    }
  }

  function montarUrlParcelas(dividaId) {
    const baseUrl = window.location.pathname.replace(/add\/$|[^/]+\/change\/$/, "");
    return `${baseUrl}parcelas-por-divida/?divida_id=${encodeURIComponent(dividaId)}`;
  }

  function limparValorPagamento() {
    valorPagamentoField.value = "";
  }

  async function carregarParcelas(dividaId) {
    if (!dividaId) {
      limparParcelas();
      limparValorPagamento();
      return;
    }

    const requestId = ++ultimoRequestId;
    setLoadingParcelas();
    limparValorPagamento();

    try {
      const response = await fetch(montarUrlParcelas(dividaId), {
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      });

      if (!response.ok) {
        throw new Error("Erro ao buscar parcelas");
      }

      const data = await response.json();

      if (requestId !== ultimoRequestId) {
        return;
      }

      preencherParcelas(data.parcelas || []);
    } catch (error) {
      console.error(error);

      if (requestId !== ultimoRequestId) {
        return;
      }

      limparParcelas("Erro ao carregar parcelas");
      limparValorPagamento();
    }
  }

  function preencherValorPagamento() {
    const selectedOption = parcelaField.options[parcelaField.selectedIndex];

    if (!selectedOption || !selectedOption.dataset.valorPendentePagamento) {
      limparValorPagamento();
      return;
    }

    valorPagamentoField.value = selectedOption.dataset.valorPendentePagamento;
  }

  dividaField.addEventListener("change", function () {
    carregarParcelas(this.value);
  });

  parcelaField.addEventListener("change", function () {
    preencherValorPagamento();
  });
});
// novo
document.addEventListener("DOMContentLoaded", function () {
  const campoData = document.querySelector("#id_data_pagamento");
  if (campoData && !campoData.value) {
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = String(hoje.getMonth() + 1).padStart(2, "0");
    const dia = String(hoje.getDate()).padStart(2, "0");
    campoData.value = `${ano}-${mes}-${dia}`;
  }
});
