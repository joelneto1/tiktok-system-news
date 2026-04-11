export const VIDEO_MODELS = [
  {
    id: 'news_tradicional',
    name: 'News Tradicional',
    description: 'Breaking news com avatar + B-Rolls dinâmicos',
    active: true,
  },
  {
    id: 'news_jornalistico',
    name: 'News Jornalístico',
    description: 'Formato jornalístico profissional',
    active: false,
    comingSoon: true,
  },
  {
    id: 'news_ice',
    name: 'News ICE',
    description: 'Estilo ICE de alta retenção',
    active: false,
    comingSoon: true,
  },
] as const

export const PIPELINE_STAGES = [
  { id: 'research', name: 'Research', description: 'Coleta e análise de fontes' },
  { id: 'script', name: 'Script', description: 'Geração do roteiro' },
  { id: 'voice', name: 'Voice', description: 'Síntese de voz (TTS)' },
  { id: 'avatar', name: 'Avatar', description: 'Geração do avatar falando' },
  { id: 'broll', name: 'B-Roll', description: 'Busca e seleção de B-Rolls' },
  { id: 'edit', name: 'Edit', description: 'Edição e composição final' },
  { id: 'caption', name: 'Caption', description: 'Legendas e captions' },
  { id: 'export', name: 'Export', description: 'Exportação do vídeo final' },
] as const
