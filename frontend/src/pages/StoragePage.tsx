import { useState, useEffect, useCallback } from 'react'
import {
  Folder,
  FileText,
  FileAudio,
  FileVideo,
  Download,
  Trash2,
  ChevronRight,
  HardDrive,
  Play,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  browseStorage,
  getDownloadUrl,
  deleteStorageFile,
  type StorageObject,
} from '@/api/storage'

interface FileItem {
  name: string
  type: 'folder' | 'json' | 'mp3' | 'mp4' | 'webm' | 'txt'
  size?: string
  date?: string
}

function getFileType(obj: StorageObject): FileItem['type'] {
  if (obj.is_dir) return 'folder'
  const ext = obj.name.split('.').pop()?.toLowerCase() ?? ''
  if (['mp4', 'webm'].includes(ext)) return ext as FileItem['type']
  if (ext === 'mp3') return 'mp3'
  if (ext === 'json') return 'json'
  return 'txt'
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const FILE_ICONS: Record<string, typeof FileText> = {
  folder: Folder,
  json: FileText,
  mp3: FileAudio,
  mp4: FileVideo,
  webm: FileVideo,
  txt: FileText,
}

const FILE_COLORS: Record<string, string> = {
  folder: 'text-cyan-400',
  json: 'text-yellow-400',
  mp3: 'text-green-400',
  mp4: 'text-purple-400',
  webm: 'text-purple-400',
  txt: 'text-slate-400',
}

export default function StoragePage() {
  const [currentPath, setCurrentPath] = useState<string[]>(['news-factory'])
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [files, setFiles] = useState<FileItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const prefix = currentPath.length > 1 ? currentPath.slice(1).join('/') + '/' : ''

  const fetchFiles = useCallback(async () => {
    setIsLoading(true)
    try {
      const resp = await browseStorage(prefix || undefined)
      const items: FileItem[] = resp.objects.map((obj) => ({
        name: obj.name.replace(/\/$/, '').split('/').pop() ?? obj.name,
        type: getFileType(obj),
        size: obj.is_dir ? undefined : formatSize(obj.size),
        date: obj.last_modified
          ? new Date(obj.last_modified).toLocaleString('pt-BR', {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
            })
          : undefined,
      }))
      setFiles(items)
    } catch {
      // API not available — show empty
      setFiles([])
    } finally {
      setIsLoading(false)
    }
  }, [prefix])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  function navigateToFolder(name: string) {
    setCurrentPath((prev) => [...prev, name])
    setSelectedFile(null)
  }

  function navigateToBreadcrumb(index: number) {
    setCurrentPath((prev) => prev.slice(0, index + 1))
    setSelectedFile(null)
  }

  function handleDownload(file: FileItem) {
    const filePath = [...currentPath.slice(1), file.name].join('/')
    window.open(getDownloadUrl(filePath), '_blank')
  }

  async function handleDelete(file: FileItem) {
    const filePath = [...currentPath.slice(1), file.name].join('/')
    try {
      await deleteStorageFile(filePath)
      setFiles((prev) => prev.filter((f) => f.name !== file.name))
      if (selectedFile?.name === file.name) setSelectedFile(null)
    } catch {
      console.error('Failed to delete file', filePath)
    }
  }

  const isMediaFile = selectedFile && ['mp3', 'mp4', 'webm'].includes(selectedFile.type)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          <span className="text-cyan-400">Storage</span>
        </h2>
        <p className="text-text-secondary text-sm mt-1">
          Navegue pelos arquivos do MinIO.
        </p>
      </div>

      {/* Breadcrumb */}
      <div className="flex items-center gap-1 text-sm">
        <HardDrive className="w-4 h-4 text-text-secondary mr-1" />
        {currentPath.map((segment, i) => (
          <div key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="w-3 h-3 text-text-secondary" />}
            <button
              onClick={() => navigateToBreadcrumb(i)}
              className={cn(
                'px-1.5 py-0.5 rounded transition-colors',
                i === currentPath.length - 1
                  ? 'text-cyan-400 font-medium'
                  : 'text-text-secondary hover:text-text-primary',
              )}
            >
              {segment}
            </button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* File list */}
        <div className="lg:col-span-2 bg-surface border border-border rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 animate-spin text-accent" />
              <span className="ml-2 text-sm text-text-secondary">Carregando...</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-text-secondary text-xs">
                    <th className="text-left px-4 py-3 font-medium"></th>
                    <th className="text-left px-4 py-3 font-medium">Nome</th>
                    <th className="text-left px-4 py-3 font-medium">Tamanho</th>
                    <th className="text-left px-4 py-3 font-medium">Tipo</th>
                    <th className="text-left px-4 py-3 font-medium">Data</th>
                    <th className="text-left px-4 py-3 font-medium">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => {
                    const Icon = FILE_ICONS[file.type] || FileText
                    const color = FILE_COLORS[file.type] || 'text-slate-400'
                    return (
                      <tr
                        key={file.name}
                        onClick={() => {
                          if (file.type === 'folder') {
                            navigateToFolder(file.name)
                          } else {
                            setSelectedFile(file)
                          }
                        }}
                        className={cn(
                          'border-b border-border/50 cursor-pointer transition-colors',
                          selectedFile?.name === file.name
                            ? 'bg-accent/5'
                            : 'hover:bg-surface-hover/50',
                        )}
                      >
                        <td className="px-4 py-2.5">
                          <Icon className={cn('w-4 h-4', color)} />
                        </td>
                        <td className="px-4 py-2.5 text-text-primary font-mono text-xs">
                          {file.name}
                        </td>
                        <td className="px-4 py-2.5 text-text-secondary text-xs font-mono">
                          {file.size || '--'}
                        </td>
                        <td className="px-4 py-2.5 text-text-secondary text-xs uppercase">
                          {file.type}
                        </td>
                        <td className="px-4 py-2.5 text-text-secondary text-xs font-mono">
                          {file.date || '--'}
                        </td>
                        <td className="px-4 py-2.5">
                          {file.type !== 'folder' && (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={(e) => { e.stopPropagation(); handleDownload(file) }}
                                className="p-1 rounded text-text-secondary hover:text-cyan-400 transition-colors"
                                title="Download"
                              >
                                <Download className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleDelete(file) }}
                                className="p-1 rounded text-text-secondary hover:text-red-400 transition-colors"
                                title="Excluir"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                  {files.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-text-secondary text-sm">
                        Pasta vazia.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Preview panel */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Preview</h3>
          {selectedFile ? (
            <div className="space-y-3">
              <div className="bg-black rounded-lg border border-[#1e293b] aspect-video flex items-center justify-center">
                {isMediaFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <Play className="w-8 h-8 text-cyan-400" />
                    <span className="text-xs text-slate-500 font-mono">{selectedFile.name}</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="w-8 h-8 text-slate-600" />
                    <span className="text-xs text-slate-500 font-mono">Preview indisponivel</span>
                  </div>
                )}
              </div>
              <div className="space-y-1.5">
                <p className="text-xs font-mono text-text-primary">{selectedFile.name}</p>
                <p className="text-xs text-text-secondary">Tamanho: {selectedFile.size}</p>
                <p className="text-xs text-text-secondary">Tipo: {selectedFile.type.toUpperCase()}</p>
                {selectedFile.date && (
                  <p className="text-xs text-text-secondary">Data: {selectedFile.date}</p>
                )}
              </div>
            </div>
          ) : (
            <div className="text-xs text-text-secondary text-center py-8">
              Selecione um arquivo para visualizar.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
