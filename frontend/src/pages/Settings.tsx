import { useState, useEffect } from 'react'
import { cn } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  Database,
  HardDrive,
  Shield,
  Bell,
  Palette,
  Github,
  ExternalLink,
  Save,
  Sparkles,
  Bot,
  Search,
} from 'lucide-react'

interface SettingsState {
  nebiusBaseUrl: string
  nebiusModel: string
  workspaceRoot: string
  defaultRiskLevel: string
  maxFileSize: number
  autoScan: boolean
  notifications: boolean
  theme: string
  demoMode: boolean
}

interface TextField {
  key: string
  label: string
  type: 'text' | 'password' | 'number'
  placeholder?: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
}

interface SelectField {
  key: string
  label: string
  type: 'select'
  options: string[]
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
}

interface CheckboxField {
  key: string
  label: string
  type: 'checkbox'
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  checked?: boolean
}

type Field = TextField | SelectField | CheckboxField

interface Section {
  title: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  description: string
  fields: Field[]
  action?: {
    label: string
    onClick: () => void
    loading: boolean
    icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  }

}

export function Settings() {
    const { demoMode, setDemoMode } = useDevSweep()
    const [settings, setSettings] = useState<SettingsState>({
        nebiusBaseUrl: 'https://api.tokenfactory.us-central1.nebius.com/v1/',
        nebiusModel: 'nvidia/nemotron-3-super-120b-a12b',
        workspaceRoot: '',
        defaultRiskLevel: 'SAFE',
        maxFileSize: 100,
        autoScan: false,
        notifications: true,
        theme: 'dark',
        demoMode: false,
      })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // Load from localStorage
    const stored = localStorage.getItem('devsweep-settings')
    if (stored) {
      setSettings(JSON.parse(stored))
    }
    // Load from env if available
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        setSettings(prev => ({ ...prev, workspaceRoot: data.workspace_root || '' }))
      })
      .catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    localStorage.setItem('devsweep-settings', JSON.stringify(settings))
    setSaved(true)
    setSaving(false)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleDemoToggle = (enabled: boolean) => {
    setDemoMode(enabled)
    setSettings(prev => ({ ...prev, demoMode: enabled }))
  }

  const sections = [
    {
          title: 'AI Provider',
          icon: Bot,
          description: 'Configure NVIDIA Nemotron via Nebius Token Factory. API key must be set in backend environment (NEBIUS_API_KEY).',
          fields: [
            { key: 'nebiusBaseUrl', label: 'Base URL', type: 'text' as const, placeholder: 'https://api.tokenfactory.us-central1.nebius.com/v1/', icon: ExternalLink },
            { key: 'nebiusModel', label: 'Model', type: 'select' as const, options: ['nvidia/nemotron-3-super-120b-a12b', 'nvidia/nemotron-3-5-lightning', 'nvidia/nemotron-4-ultra'], icon: Sparkles },
          ],
        },
    {
      title: 'Workspace',
      icon: Database,
      description: 'Configure scan targets and defaults',
      fields: [
        { key: 'workspaceRoot', label: 'Workspace Root', type: 'text' as const, placeholder: '/path/to/projects', icon: Database },
        { key: 'defaultRiskLevel', label: 'Default Risk Level', type: 'select' as const, options: ['SAFE', 'CAUTION', 'DANGEROUS'], icon: Shield },
        { key: 'maxFileSize', label: 'Max File Size (MB)', type: 'number' as const, placeholder: '100', icon: HardDrive },
        { key: 'autoScan', label: 'Auto-scan on startup', type: 'checkbox' as const, icon: Search },
      ],
    },
    {
      title: 'UI Preferences',
      icon: Palette,
      description: 'Customize the interface',
      fields: [
        { key: 'theme', label: 'Theme', type: 'select' as const, options: ['dark', 'light', 'system'], icon: Palette },
        { key: 'notifications', label: 'Enable notifications', type: 'checkbox' as const, icon: Bell },
      ],
    },
    {
      title: 'Demo Mode',
      icon: Sparkles,
      description: 'Use deterministic demo project for testing',
      fields: [
        { key: 'demoMode', label: 'Enable Demo Mode', type: 'checkbox' as const, icon: Sparkles, checked: demoMode },
      ],
      action: { label: demoMode ? 'Disable Demo' : 'Enable Demo', onClick: () => handleDemoToggle(!demoMode), loading: false, icon: Sparkles },
    },
  ]

  return (
      <div className="space-y-6 animate-in max-w-3xl">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-devsweep-textSecondary mt-1">Configure DevSweep AI behavior and integrations</p>
        </div>

        {sections.map((section, si) => (
        <div key={si} className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden">
          <div className="p-6 border-b border-devsweep-border bg-devsweep-bgTertiary/50">
            <div className="flex items-center gap-3">
              <section.icon className="w-6 h-6 text-devsweep-accent" />
              <div>
                <h2 className="font-semibold">{section.title}</h2>
                <p className="text-xs text-devsweep-textMuted">{section.description}</p>
              </div>
            </div>
          </div>
          <div className="p-6 space-y-6">
            {section.fields.map((field, fi) => (
              <div key={fi} className="space-y-2">
                <label className="block text-sm font-medium">{field.label}</label>
                {field.type === 'text' && (
                  <input
                    type="text"
                    value={settings[field.key as keyof typeof settings] as string}
                    onChange={(e) => setSettings(prev => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={field.placeholder}
                    className="w-full px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text placeholder-devsweep-textMuted focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent"
                  />
                )}
                {field.type === 'password' && (
                  <input
                    type="password"
                    value={settings[field.key as keyof typeof settings] as string}
                    onChange={(e) => setSettings(prev => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={field.placeholder}
                    className="w-full px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text placeholder-devsweep-textMuted focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent"
                  />
                )}
                {field.type === 'number' && (
                  <input
                    type="number"
                    value={settings[field.key as keyof typeof settings] as number}
                    onChange={(e) => setSettings(prev => ({ ...prev, [field.key]: Number(e.target.value) }))}
                    placeholder={field.placeholder}
                    className="w-full px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text placeholder-devsweep-textMuted focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent"
                  />
                )}
                {field.type === 'select' && (
                  <select
                    value={settings[field.key as keyof typeof settings] as string}
                    onChange={(e) => setSettings(prev => ({ ...prev, [field.key]: e.target.value }))}
                    className="w-full px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent"
                  >
                    {field.options!.map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                )}
                {field.type === 'checkbox' && (
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(field as CheckboxField).checked !== undefined ? (field as CheckboxField).checked : (settings[field.key as keyof SettingsState] as boolean)}
                      onChange={(e) => {
                        if (field.key === 'demoMode') {
                          handleDemoToggle(e.target.checked)
                        } else {
                          setSettings(prev => ({ ...prev, [field.key]: e.target.checked }))
                        }
                      }}
                      className="w-4 h-4 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent"
                    />
                    <span className="text-sm">{field.label}</span>
                  </label>
                )}
              </div>
            ))}
            {section.action && (
              <button
                onClick={section.action.onClick}
                disabled={section.action.loading || saving}
                className={cn('px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
                  section.action.loading || testing 
                    ? 'bg-devsweep-bg border border-devsweep-border text-devsweep-textMuted' 
                    : 'bg-devsweep-accent text-devsweep-bg hover:bg-devsweep-accentHover'
                )}
              >
                {section.action.loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <section.action.icon className="w-4 h-4" />}
                {section.action.label}
              </button>
            )}
          </div>
        </div>
      ))}

      <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Save className="w-5 h-5" />
          Save All Settings
        </h2>
        <p className="text-devsweep-textSecondary mb-4">Settings are stored locally in your browser. For API keys, also set the NEBIUS_API_KEY environment variable for the backend.</p>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors flex items-center gap-2"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>

      <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Github className="w-5 h-5" />
          Links & Resources
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <a href="https://studio.nebius.ai/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg hover:border-devsweep-accent/50 transition-colors">
            <ExternalLink className="w-4 h-4 text-devsweep-textMuted" />
            <span>Nebius AI Studio</span>
          </a>
          <a href="https://github.com/nvidia/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg hover:border-devsweep-accent/50 transition-colors">
            <Github className="w-4 h-4 text-devsweep-textMuted" />
            <span>NVIDIA on GitHub</span>
          </a>
          <a href="https://github.com/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg hover:border-devsweep-accent/50 transition-colors">
            <Github className="w-4 h-4 text-devsweep-textMuted" />
            <span>DevSweep Repository</span>
          </a>
          <a href="#" className="flex items-center gap-2 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg hover:border-devsweep-accent/50 transition-colors">
            <ExternalLink className="w-4 h-4 text-devsweep-textMuted" />
            <span>Documentation</span>
          </a>
        </div>
      </div>
    </div>
  )
}