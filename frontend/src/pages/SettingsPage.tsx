import { useState, useEffect } from 'react'
import { Eye, EyeOff, Loader2, CheckCircle2, XCircle, Save, Mic, Brain, AudioWaveform, HardDrive, Sliders } from 'lucide-react'
import { cn } from '@/lib/utils'
import { listSettings, bulkUpdateSettings, updateSetting, testSetting } from '@/api/settings'

/* ──────────────────────────────────────────────
   Reusable Field Components
   ────────────────────────────────────────────── */

function ApiKeyField({ label, value, onChange, onTest, testStatus = 'idle' }: {
  label: string; value: string; onChange: (v: string) => void
  onTest?: () => void; testStatus?: 'idle' | 'testing' | 'success' | 'error'
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-text-secondary">{label}</label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={visible ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="sk-..."
            className="w-full px-4 py-2.5 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent pr-10"
          />
          <button type="button" onClick={() => setVisible(!visible)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors">
            {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {onTest && (
          <button onClick={onTest} disabled={testStatus === 'testing'}
            className={cn(
              'px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 shrink-0',
              testStatus === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                : testStatus === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                : 'bg-surface border border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover',
            )}>
            {testStatus === 'testing' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {testStatus === 'success' && <CheckCircle2 className="w-3.5 h-3.5" />}
            {testStatus === 'error' && <XCircle className="w-3.5 h-3.5" />}
            Testar
          </button>
        )}
      </div>
    </div>
  )
}

function TextField({ label, value, onChange, type = 'text', placeholder, mono, description }: {
  label: string; value: string; onChange: (v: string) => void
  type?: string; placeholder?: string; mono?: boolean; description?: string
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-text-secondary">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className={cn(
          'w-full px-4 py-2.5 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
          mono && 'font-mono',
        )} />
      {description && <p className="text-xs text-text-secondary/70">{description}</p>}
    </div>
  )
}

function SelectField({ label, value, onChange, options, description }: {
  label: string; value: string; onChange: (v: string) => void
  options: { value: string; label: string }[]; description?: string
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-text-secondary">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 rounded-lg bg-background border border-border text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent">
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {description && <p className="text-xs text-text-secondary/70">{description}</p>}
    </div>
  )
}

function NumberField({ label, value, onChange, placeholder, min, max, step, description }: {
  label: string; value: string; onChange: (v: string) => void
  placeholder?: string; min?: number; max?: number; step?: number; description?: string
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-text-secondary">{label}</label>
      <input type="number" value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} min={min} max={max} step={step}
        className="w-full px-4 py-2.5 rounded-lg bg-background border border-border text-text-primary placeholder:text-text-secondary/50 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent" />
      {description && <p className="text-xs text-text-secondary/70">{description}</p>}
    </div>
  )
}

function SectionCard({ icon: Icon, title, subtitle, accentColor, children, onSave, isSaving, saveSuccess, testMessage }: {
  icon: React.ElementType; title: string; subtitle: string; accentColor: string; children: React.ReactNode
  onSave?: () => void; isSaving?: boolean; saveSuccess?: boolean; testMessage?: string
}) {
  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <div className={cn('px-6 py-4 border-b border-border flex items-center gap-3', accentColor)}>
        <div className="p-2 rounded-lg bg-background/50">
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary">{subtitle}</p>
        </div>
        {/* Save button on the right side of header */}
        {onSave && (
          <div className="flex items-center gap-2">
            {saveSuccess && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Salvo!
              </span>
            )}
            {testMessage && (
              <span className={cn('text-xs max-w-[200px] truncate', testMessage.includes('OK') || testMessage.includes('Conectado') ? 'text-green-400' : 'text-red-400')}>
                {testMessage}
              </span>
            )}
            <button onClick={onSave} disabled={isSaving}
              className="px-4 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-600 text-white text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5 shrink-0">
              {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
              Salvar
            </button>
          </div>
        )}
      </div>
      <div className="p-6 space-y-4">
        {children}
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Settings Page
   ────────────────────────────────────────────── */

export default function SettingsPage() {
  const [isLoading, setIsLoading] = useState(true)
  const [_saving, setSaving] = useState(false)

  // Per-card save state
  const [cardSaving, setCardSaving] = useState<Record<string, boolean>>({})
  const [cardSuccess, setCardSuccess] = useState<Record<string, boolean>>({})
  const [testMessages, setTestMessages] = useState<Record<string, string>>({})

  // Toast notification
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  function showToast(message: string, type: 'success' | 'error' = 'success') {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  // GenAIPro (TTS)
  const [genaiKey, setGenaiKey] = useState('')
  const [genaiTest, setGenaiTest] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [ttsModel, setTtsModel] = useState('eleven_multilingual_v2')
  const [voiceId, setVoiceId] = useState('')
  const [ttsSpeed, setTtsSpeed] = useState('1.0')
  const [ttsStability, setTtsStability] = useState('0.75')
  const [ttsSimilarity, setTtsSimilarity] = useState('0.5')
  const [ttsStyle, setTtsStyle] = useState('0')

  // OpenRouter (LLM)
  const [openrouterKey, setOpenrouterKey] = useState('')
  const [openrouterTest, setOpenrouterTest] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [openrouterModel, setOpenrouterModel] = useState('anthropic/claude-sonnet-4')
  const [openrouterMaxTokens, setOpenrouterMaxTokens] = useState('4096')
  const [openrouterTemperature, setOpenrouterTemperature] = useState('0.7')

  // OpenAI (Whisper)
  const [openaiKey, setOpenaiKey] = useState('')
  const [openaiTest, setOpenaiTest] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [whisperModel, setWhisperModel] = useState('whisper-1')

  // MinIO
  const [minioEndpoint, setMinioEndpoint] = useState('localhost')
  const [minioPort, setMinioPort] = useState('9000')
  const [minioAccessKey, setMinioAccessKey] = useState('')
  const [minioSecretKey, setMinioSecretKey] = useState('')
  const [minioBucket, setMinioBucket] = useState('news-videos')
  const [minioSSL, setMinioSSL] = useState(false)
  const [minioTest, setMinioTest] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')

  // Pipeline
  const [idioma, setIdioma] = useState('pt-BR')
  const [maxBrolls, setMaxBrolls] = useState('40')
  const [brollDuration, setBrollDuration] = useState('6')
  const [brollBatchSize, setBrollBatchSize] = useState('10')
  const [maxVideos, setMaxVideos] = useState('10')

  const SETTING_MAP: Record<string, (v: string) => void> = {
    genai_api_key: setGenaiKey,
    tts_model: setTtsModel,
    default_voice_id: setVoiceId,
    tts_speed: setTtsSpeed,
    tts_stability: setTtsStability,
    tts_similarity: setTtsSimilarity,
    tts_style: setTtsStyle,
    openrouter_api_key: setOpenrouterKey,
    openrouter_model: setOpenrouterModel,
    openrouter_max_tokens: setOpenrouterMaxTokens,
    openrouter_temperature: setOpenrouterTemperature,
    openai_api_key: setOpenaiKey,
    whisper_model: setWhisperModel,
    minio_endpoint: setMinioEndpoint,
    minio_port: setMinioPort,
    minio_access_key: setMinioAccessKey,
    minio_secret_key: setMinioSecretKey,
    minio_bucket: setMinioBucket,
    minio_ssl: (v) => setMinioSSL(v === 'true'),
    default_language: setIdioma,
    max_brolls: setMaxBrolls,
    broll_duration: setBrollDuration,
    broll_batch_size: setBrollBatchSize,
    max_concurrent_videos: setMaxVideos,
  }

  useEffect(() => {
    async function load() {
      try {
        const resp = await listSettings()
        const settings = Array.isArray(resp) ? resp : (resp as any).settings || []
        for (const setting of settings) {
          const setter = SETTING_MAP[setting.key]
          if (setter && setting.value) setter(setting.value)
        }
      } catch { /* API not available */ }
      finally { setIsLoading(false) }
    }
    load()
  }, [])

  async function handleTest(key: string, setter: (s: 'idle' | 'testing' | 'success' | 'error') => void, cardKey: string) {
    setter('testing')
    setTestMessages((prev) => ({ ...prev, [cardKey]: '' }))
    try {
      // Save the key first, then test
      const keyValue = getKeyValue(key)
      if (keyValue) {
        await updateSetting(key, keyValue)
      }
      const result = await testSetting(key)
      setter(result.success ? 'success' : 'error')
      setTestMessages((prev) => ({ ...prev, [cardKey]: result.message }))
    } catch (err) {
      setter('error')
      setTestMessages((prev) => ({ ...prev, [cardKey]: 'Erro ao testar conexao' }))
    }
  }

  function getKeyValue(key: string): string {
    const map: Record<string, string> = {
      genai_api_key: genaiKey, genaipro_api_key: genaiKey,
      openrouter_api_key: openrouterKey,
      openai_api_key: openaiKey,
    }
    return map[key] || ''
  }

  async function saveCard(cardKey: string, settings: Record<string, string>) {
    setCardSaving((prev) => ({ ...prev, [cardKey]: true }))
    setCardSuccess((prev) => ({ ...prev, [cardKey]: false }))
    try {
      await bulkUpdateSettings(settings)
      setCardSuccess((prev) => ({ ...prev, [cardKey]: true }))
      showToast('Configuracoes salvas com sucesso!', 'success')
      setTimeout(() => setCardSuccess((prev) => ({ ...prev, [cardKey]: false })), 4000)
    } catch (err) {
      console.error('Save failed:', err)
      showToast('Erro ao salvar configuracoes', 'error')
    } finally {
      setCardSaving((prev) => ({ ...prev, [cardKey]: false }))
    }
  }

  async function _handleSave() {
    setSaving(true)
    try {
      await bulkUpdateSettings({
        genai_api_key: genaiKey,
        tts_model: ttsModel,
        default_voice_id: voiceId,
        tts_speed: ttsSpeed,
        tts_stability: ttsStability,
        tts_similarity: ttsSimilarity,
        tts_style: ttsStyle,
        openrouter_api_key: openrouterKey,
        openrouter_model: openrouterModel,
        openrouter_max_tokens: openrouterMaxTokens,
        openrouter_temperature: openrouterTemperature,
        openai_api_key: openaiKey,
        whisper_model: whisperModel,
        minio_endpoint: minioEndpoint,
        minio_port: minioPort,
        minio_access_key: minioAccessKey,
        minio_secret_key: minioSecretKey,
        minio_bucket: minioBucket,
        minio_ssl: String(minioSSL),
        default_language: idioma,
        max_brolls: maxBrolls,
        broll_duration: brollDuration,
        broll_batch_size: brollBatchSize,
        max_concurrent_videos: maxVideos,
      })
    } catch { /* silently fail */ }
    finally { setSaving(false) }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
        <span className="ml-2 text-text-secondary">Carregando...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-text-primary">Configuracoes</h2>
        <p className="text-text-secondary text-sm mt-1">Ajuste as configuracoes do sistema e integracoes.</p>
      </div>

      {/* Toast notification — fixed bottom-right */}
      {toast && (
        <div
          className={cn(
            'fixed top-20 right-6 z-[100] px-5 py-3.5 rounded-xl shadow-2xl flex items-center gap-3',
            'backdrop-blur-md border',
            'animate-[slideIn_0.3s_ease-out]',
            toast.type === 'success'
              ? 'bg-green-500/20 border-green-500/40 text-green-300'
              : 'bg-red-500/20 border-red-500/40 text-red-300',
          )}
          style={{ animation: 'slideIn 0.3s ease-out' }}
        >
          {toast.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 shrink-0" />
          )}
          <span className="text-sm font-medium">{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2 opacity-60 hover:opacity-100 transition-opacity">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>

      {/* Row 1: GenAIPro + OpenRouter */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

      {/* ── GenAIPro (TTS) ── */}
      <SectionCard
        icon={Mic}
        title="GenAIPro — Text-to-Speech"
        subtitle="Configuracoes de voz, modelo TTS e parametros de geracao de audio"
        accentColor="text-purple-400"
        onSave={() => saveCard('genai', { genai_api_key: genaiKey, tts_model: ttsModel, default_voice_id: voiceId, tts_speed: ttsSpeed, tts_stability: ttsStability, tts_similarity: ttsSimilarity, tts_style: ttsStyle })}
        isSaving={cardSaving['genai']}
        saveSuccess={cardSuccess['genai']}
        testMessage={testMessages['genai']}
      >
        <ApiKeyField
          label="API Key"
          value={genaiKey}
          onChange={setGenaiKey}
          onTest={() => handleTest('genai_api_key', setGenaiTest, 'genai')}
          testStatus={genaiTest}
        />
        <div className="border-t border-border/50 pt-4 mt-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SelectField
            label="Modelo TTS"
            value={ttsModel}
            onChange={setTtsModel}
            options={[
              { value: 'eleven_multilingual_v2', label: 'Multilingual V2 (Recomendado)' },
              { value: 'eleven_turbo_v2_5', label: 'Turbo V2.5 (Rapido)' },
              { value: 'eleven_flash_v2_5', label: 'Flash V2.5 (Mais rapido)' },
              { value: 'eleven_v3', label: 'V3 (Mais recente)' },
            ]}
            description="Modelo de geracao de voz da GenAIPro"
          />
          <TextField
            label="Voice ID Padrao"
            value={voiceId}
            onChange={setVoiceId}
            placeholder="JBFqnCBsd6RMkjVDRZzb"
            mono
            description="ID da voz padrao (consulte /voices para listar)"
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <NumberField
            label="Velocidade"
            value={ttsSpeed}
            onChange={setTtsSpeed}
            min={0.7} max={1.2} step={0.05}
            description="0.7 a 1.2"
          />
          <NumberField
            label="Estabilidade"
            value={ttsStability}
            onChange={setTtsStability}
            min={0} max={1} step={0.05}
            description="0 a 1"
          />
          <NumberField
            label="Similaridade"
            value={ttsSimilarity}
            onChange={setTtsSimilarity}
            min={0} max={1} step={0.05}
            description="0 a 1"
          />
          <NumberField
            label="Estilo"
            value={ttsStyle}
            onChange={setTtsStyle}
            min={0} max={1} step={0.05}
            description="0 a 1"
          />
        </div>
      </SectionCard>

      {/* ── OpenRouter (LLM) ── */}
      <SectionCard
        icon={Brain}
        title="OpenRouter — LLM (Roteiro + Diretor de Cena)"
        subtitle="Modelo de linguagem para geracao de roteiros e direcao de cena"
        accentColor="text-cyan-400"
        onSave={() => saveCard('openrouter', { openrouter_api_key: openrouterKey, openrouter_model: openrouterModel, openrouter_max_tokens: openrouterMaxTokens, openrouter_temperature: openrouterTemperature })}
        isSaving={cardSaving['openrouter']}
        saveSuccess={cardSuccess['openrouter']}
        testMessage={testMessages['openrouter']}
      >
        <ApiKeyField
          label="API Key"
          value={openrouterKey}
          onChange={setOpenrouterKey}
          onTest={() => handleTest('openrouter_api_key', setOpenrouterTest, 'openrouter')}
          testStatus={openrouterTest}
        />
        <div className="border-t border-border/50 pt-4 mt-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SelectField
            label="Modelo LLM"
            value={openrouterModel}
            onChange={setOpenrouterModel}
            options={[
              { value: 'anthropic/claude-sonnet-4', label: 'Claude Sonnet 4 (Recomendado)' },
              { value: 'anthropic/claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' },
              { value: 'anthropic/claude-3-haiku', label: 'Claude 3 Haiku (Rapido)' },
              { value: 'openai/gpt-4o', label: 'GPT-4o' },
              { value: 'openai/gpt-4o-mini', label: 'GPT-4o Mini (Economico)' },
              { value: 'google/gemini-pro-1.5', label: 'Gemini Pro 1.5' },
              { value: 'meta-llama/llama-3.1-70b-instruct', label: 'Llama 3.1 70B' },
            ]}
            description="Modelo usado para gerar roteiros e direcionar cenas"
          />
          <NumberField
            label="Max Tokens"
            value={openrouterMaxTokens}
            onChange={setOpenrouterMaxTokens}
            min={512} max={32000} step={512}
            description="Limite maximo de tokens na resposta (512-32000)"
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <NumberField
            label="Temperatura"
            value={openrouterTemperature}
            onChange={setOpenrouterTemperature}
            min={0} max={2} step={0.1}
            description="Criatividade: 0 = deterministico, 1 = criativo, 2 = muito aleatorio"
          />
        </div>
      </SectionCard>

      </div>{/* End Row 1 */}

      {/* Row 2: OpenAI + MinIO */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

      {/* ── OpenAI (Whisper) ── */}
      <SectionCard
        icon={AudioWaveform}
        title="OpenAI — Whisper (Transcricao)"
        subtitle="API de transcricao de audio para timestamps palavra a palavra"
        onSave={() => saveCard('openai', { openai_api_key: openaiKey, whisper_model: whisperModel })}
        isSaving={cardSaving['openai']}
        saveSuccess={cardSuccess['openai']}
        testMessage={testMessages['openai']}
        accentColor="text-green-400"
      >
        <ApiKeyField
          label="API Key"
          value={openaiKey}
          onChange={setOpenaiKey}
          onTest={() => handleTest('openai_api_key', setOpenaiTest, 'openai')}
          testStatus={openaiTest}
        />
        <div className="border-t border-border/50 pt-4 mt-4" />
        <SelectField
          label="Modelo Whisper"
          value={whisperModel}
          onChange={setWhisperModel}
          options={[
            { value: 'whisper-1', label: 'Whisper-1 (Padrao)' },
          ]}
          description="Modelo de transcricao de audio"
        />
      </SectionCard>

      {/* ── MinIO Storage ── */}
      <SectionCard
        icon={HardDrive}
        title="MinIO — Storage"
        subtitle="Armazenamento de objetos para assets e videos gerados"
        accentColor="text-orange-400"
        onSave={() => saveCard('minio', { minio_endpoint: minioEndpoint, minio_port: minioPort, minio_access_key: minioAccessKey, minio_secret_key: minioSecretKey, minio_bucket: minioBucket, minio_ssl: String(minioSSL) })}
        isSaving={cardSaving['minio']}
        saveSuccess={cardSuccess['minio']}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <TextField label="Endpoint" value={minioEndpoint} onChange={setMinioEndpoint} placeholder="minio-api.exemplo.com" mono />
          <TextField label="Porta" value={minioPort} onChange={setMinioPort} type="number" placeholder="9000" mono />
          <TextField label="Access Key" value={minioAccessKey} onChange={setMinioAccessKey} mono />
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-text-secondary">Secret Key</label>
            <div className="relative">
              <input type="password" value={minioSecretKey} onChange={(e) => setMinioSecretKey(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-background border border-border text-text-primary text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent" />
            </div>
          </div>
          <TextField label="Bucket" value={minioBucket} onChange={setMinioBucket} placeholder="news-videos" mono />
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-text-secondary">SSL (HTTPS)</label>
            <div className="flex items-center gap-3 h-[42px] px-4 rounded-lg bg-background border border-border">
              <button onClick={() => setMinioSSL(!minioSSL)}
                className={cn('relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0', minioSSL ? 'bg-green-500' : 'bg-slate-600')}>
                <span className={cn('absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200',
                  minioSSL && 'translate-x-5')} />
              </button>
              <span className="text-sm text-text-primary">{minioSSL ? 'Ativado' : 'Desativado'}</span>
            </div>
          </div>
        </div>
        <button onClick={() => handleTest('minio_ssl', setMinioTest, 'minio')} disabled={minioTest === 'testing'}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2',
            minioTest === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20'
              : minioTest === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/20'
              : 'bg-surface-hover border border-border text-text-secondary hover:text-text-primary',
          )}>
          {minioTest === 'testing' && <Loader2 className="w-4 h-4 animate-spin" />}
          {minioTest === 'success' && <CheckCircle2 className="w-4 h-4" />}
          {minioTest === 'error' && <XCircle className="w-4 h-4" />}
          Testar Conexao
        </button>
      </SectionCard>

      </div>{/* End Row 2 */}

      {/* Row 3: Pipeline + (futuro card) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

      {/* ── Pipeline Geral ── */}
      <SectionCard
        icon={Sliders}
        title="Pipeline — Configuracoes Gerais"
        subtitle="Parametros globais de geracao de video"
        accentColor="text-yellow-400"
        onSave={() => saveCard('pipeline', { max_brolls: maxBrolls, broll_duration: brollDuration, broll_batch_size: brollBatchSize, max_concurrent_videos: maxVideos })}
        isSaving={cardSaving['pipeline']}
        saveSuccess={cardSuccess['pipeline']}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <NumberField label="Max B-Rolls por video" value={maxBrolls} onChange={setMaxBrolls}
            min={5} max={30} description="Quantidade maxima de B-Rolls gerados (5-30)" />
          <NumberField label="Duracao B-Roll (segundos)" value={brollDuration} onChange={setBrollDuration}
            min={2} max={10} description="Duracao de cada B-Roll — take completo do Grok (2-10s, padrao 6s)" />
          <NumberField label="Max Abas Simultaneas (Grok)" value={brollBatchSize} onChange={setBrollBatchSize}
            min={1} max={40} description="Limite maximo de abas abertas por vez no Grok (1-40)" />
          <NumberField label="Max Videos Simultaneos" value={maxVideos} onChange={setMaxVideos}
            min={1} max={20} description="Videos processados ao mesmo tempo na fila (1-20)" />
        </div>
      </SectionCard>

      </div>{/* End Row 3 */}

      {/* Spacer at bottom */}
      <div className="pb-8" />
    </div>
  )
}
