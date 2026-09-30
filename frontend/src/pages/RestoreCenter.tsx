import { cn, formatBytes, formatDuration } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  RotateCcw,
  Package,
  Hammer,
  GitBranch,
  Play,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  Terminal,
  Download,
  Copy,
  Clock,
} from 'lucide-react'
import { useState } from 'react'

export function RestoreCenter() {
  const { currentProject } = useDevSweep()
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [executing, setExecuting] = useState<string | null>(null)
  const [output, setOutput] = useState<string>('')

  // Mock restore options based on current project
  const restoreOptions = currentProject ? [
    {
      name: 'Restore Dependencies',
      description: 'Reinstall all project dependencies from lock files',
      commands: currentProject.project_type === 'node' 
        ? ['npm install'] 
        : currentProject.project_type === 'python'
        ? ['python -m venv .venv', 'source .venv/bin/activate', 'pip install -r requirements.txt']
        : ['make install'],
      estimated_time_seconds: 120,
      risk: 'SAFE' as 'SAFE' | 'CAUTION' | 'DANGEROUS',
      icon: Package,
    },
    {
      name: 'Restore Build',
      description: 'Rebuild the project from source',
      commands: currentProject.project_type === 'node'
        ? ['npm run build']
        : currentProject.project_type === 'python'
        ? ['python -m pytest', 'python setup.py build']
        : ['make build'],
      estimated_time_seconds: 60,
      risk: 'SAFE' as 'SAFE' | 'CAUTION' | 'DANGEROUS',
      icon: Hammer,
    },
    {
      name: 'Full Project Setup',
      description: 'Complete environment reconstruction from Git',
      commands: [
        'git clone <repository-url>',
        'cd <project>',
        currentProject.project_type === 'node' ? 'npm install' : 'python -m venv .venv && pip install -r requirements.txt',
        currentProject.project_type === 'node' ? 'npm run build' : 'python setup.py build',
      ],
      estimated_time_seconds: 300,
      risk: 'SAFE' as 'SAFE' | 'CAUTION' | 'DANGEROUS',
      icon: GitBranch,
    },
  ] : []

  const handleExecute = async (option: typeof restoreOptions[0]) => {
    setSelectedOption(option.name)
    setExecuting(option.name)
    setOutput(`$ ${option.commands.join(' && ')}\n\n[Simulated execution - connect to backend for real execution]\n\n`)
    
    // Simulate execution
    for (const cmd of option.commands) {
      await new Promise(r => setTimeout(r, 500))
      setOutput(prev => prev + `$ ${cmd}\n[Running...]\n`)
      await new Promise(r => setTimeout(r, 1000))
      setOutput(prev => prev + `[Completed]\n`)
    }
    
    setExecuting(null)
    setOutput(prev => prev + '\n✅ Restore option completed successfully!\n')
  }

  const getRiskBadge = (risk: string) => (
    <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', 
      risk === 'SAFE' && 'bg-devsweep-success/10 text-devsweep-success border border-devsweep-success/20',
      risk === 'CAUTION' && 'bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20',
      risk === 'DANGEROUS' && 'bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20'
    )}>
      {risk}
    </span>
  )

  return (
    <div className="space-y-6 animate-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Restore Center</h1>
        <p className="text-devsweep-textSecondary mt-1">Reconstruct cleaned environments and restore project state</p>
      </div>

      {!currentProject ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-12 text-center">
          <RotateCcw className="w-16 h-16 mx-auto mb-4 text-devsweep-textMuted opacity-50" />
          <h3 className="text-lg font-medium mb-2">No project selected</h3>
          <p className="text-devsweep-textMuted mb-6">Scan a workspace first to see restore options</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Project: {currentProject.project_path.split('/').pop()}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center gap-2 text-devsweep-textSecondary">
                <GitBranch className="w-4 h-4" />
                <span>Type: <span className="font-mono text-devsweep-text">{currentProject.project_type}</span></span>
              </div>
              <div className="flex items-center gap-2 text-devsweep-textSecondary">
                <Package className="w-4 h-4" />
                <span>Framework: <span className="font-mono text-devsweep-text">{currentProject.framework}</span></span>
              </div>
              <div className="flex items-center gap-2 text-devsweep-textSecondary">
                <Terminal className="w-4 h-4" />
                <span>Package Manager: <span className="font-mono text-devsweep-text">{currentProject.package_manager}</span></span>
              </div>
            </div>
          </div>

          <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden">
            <div className="p-6 border-b border-devsweep-border bg-devsweep-bgTertiary/50">
              <h2 className="text-lg font-semibold">Available Restore Options</h2>
              <p className="text-devsweep-textSecondary text-sm mt-1">Choose how to restore your project</p>
            </div>

            <div className="p-6 space-y-4">
              {restoreOptions.map((option, i) => {
                const Icon = option.icon
                const isSelected = selectedOption === option.name
                return (
                  <div
                    key={i}
                    className={cn('p-4 rounded-lg border transition-colors relative', 
                      isSelected 
                        ? 'border-devsweep-accent bg-devsweep-accent/5' 
                        : 'border-devsweep-border hover:border-devsweep-accent/50'
                    )}
                  >
                    <div className="flex items-start gap-4">
                      <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', 
                        option.risk === 'SAFE' && 'bg-devsweep-success/10 text-devsweep-success',
                        option.risk === 'CAUTION' && 'bg-devsweep-warning/10 text-devsweep-warning',
                        option.risk === 'DANGEROUS' && 'bg-devsweep-danger/10 text-devsweep-danger'
                      )}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3">
                          <h3 className="font-medium">{option.name}</h3>
                          {getRiskBadge(option.risk)}
                        </div>
                        <p className="text-devsweep-textSecondary text-sm mt-1">{option.description}</p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-devsweep-textMuted">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            ~{formatDuration(option.estimated_time_seconds)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Terminal className="w-3 h-3" />
                            {option.commands.length} command(s)
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {option.commands.map((cmd, ci) => (
                            <span key={ci} className="px-2 py-0.5 text-xs bg-devsweep-bgTertiary text-devsweep-textMuted rounded font-mono">{cmd}</span>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {executing === option.name ? (
                          <button className="px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg font-medium text-devsweep-textMuted flex items-center gap-2 disabled:opacity-50" disabled>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Running...
                          </button>
                        ) : (
                          <button
                            onClick={() => handleExecute(option)}
                            className="px-4 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors flex items-center gap-2"
                          >
                            <Play className="w-4 h-4" />
                            Execute
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {output && (
            <div className="bg-devsweep-bg border border-devsweep-border rounded-xl overflow-hidden">
              <div className="p-4 border-b border-devsweep-border bg-devsweep-bgTertiary/50 flex items-center justify-between">
                <h3 className="font-medium">Execution Output</h3>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-devsweep-bgTertiary rounded-lg transition-colors" onClick={() => navigator.clipboard.writeText(output)}>
                    <Copy className="w-4 h-4 text-devsweep-textMuted" />
                  </button>
                  <button className="p-2 hover:bg-devsweep-bgTertiary rounded-lg transition-colors">
                    <Download className="w-4 h-4 text-devsweep-textMuted" />
                  </button>
                </div>
              </div>
              <pre className="p-4 font-mono text-sm text-devsweep-textSecondary overflow-x-auto max-h-96">{output}</pre>
            </div>
          )}

          <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6">
            <h3 className="font-medium mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-devsweep-warning" />
              Prerequisites
            </h3>
            <ul className="list-disc list-inside text-devsweep-textSecondary space-y-2">
              <li>Git installed and configured</li>
              <li>{currentProject.project_type === 'node' ? 'Node.js 18+ and npm' : 'Python 3.10+ and pip'}</li>
              <li>Access to package registries (npm, PyPI, etc.)</li>
              <li>Network connectivity for dependency downloads</li>
              <li>Sufficient disk space for reconstruction</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}