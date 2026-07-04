SOURCE_PM03_SEQUENCE = [
    ("custo_fixo", "PM-03.1", "Custo fixo"),
    ("despesa_operacional", "PM-03.2", "Despesa operacional"),
    ("investimento", "PM-03.3", "Investimento"),
    ("financiamento_movimentacao", "PM-03.4", "Financiamento movimentacao"),
]

SOURCE_PM03_STEPS = {
    source: step
    for source, step, _label in SOURCE_PM03_SEQUENCE
}


def montar_posicao_sequencia_pm03(source):
    sources = [item[0] for item in SOURCE_PM03_SEQUENCE]
    if source not in sources:
        return {
            "source": source,
            "step": "",
            "label": "",
            "position": 0,
            "totalDirectSteps": len(SOURCE_PM03_SEQUENCE),
            "previousStep": "",
            "previousSource": "",
            "previousLabel": "",
            "nextStep": "",
            "nextSource": "",
            "nextLabel": "",
            "isFirstDirectStep": False,
            "isLastDirectStep": False,
            "directCanonicalFirstSequenceComplete": False,
        }

    index = sources.index(source)
    current_source, current_step, current_label = SOURCE_PM03_SEQUENCE[index]
    if index > 0:
        previous_source, previous_step, previous_label = SOURCE_PM03_SEQUENCE[index - 1]
    else:
        previous_source, previous_step, previous_label = "", "", ""

    next_index = index + 1
    if next_index < len(SOURCE_PM03_SEQUENCE):
        next_source, next_step, next_label = SOURCE_PM03_SEQUENCE[next_index]
        sequence_complete = False
    else:
        next_source = ""
        next_step = "PM-04"
        next_label = "Decisao e implementacao das origens adapter-only"
        sequence_complete = True

    return {
        "source": current_source,
        "step": current_step,
        "label": current_label,
        "position": index + 1,
        "totalDirectSteps": len(SOURCE_PM03_SEQUENCE),
        "previousStep": previous_step,
        "previousSource": previous_source,
        "previousLabel": previous_label,
        "nextStep": next_step,
        "nextSource": next_source,
        "nextLabel": next_label,
        "isFirstDirectStep": index == 0,
        "isLastDirectStep": index == len(SOURCE_PM03_SEQUENCE) - 1,
        "directCanonicalFirstSequenceComplete": sequence_complete,
    }
