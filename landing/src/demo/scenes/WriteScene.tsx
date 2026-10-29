import { Progress } from '@/components/ui/progress'
import { demoCopy } from '@/copy'
import { stageAt } from '@/demo/stages'
import { CaseHeader } from '@/demo/scenes/CaseHeader'

export function WriteScene({ t }: { t: number }) {
  const { stage, percent } = stageAt(t)
  return (
    <div>
      <CaseHeader />
      <p className="mt-6 text-base font-medium">{demoCopy.write.writing}</p>
      <p className="mt-1 text-sm text-muted-foreground @2xl:text-base">{demoCopy.write.stages[stage]}</p>
      <Progress value={percent} aria-label={demoCopy.write.writing} className="mt-3 h-2 max-w-md" />
      <p className="mt-3 max-w-prose text-sm text-muted-foreground">{demoCopy.write.help}</p>
      {/* Where the sections will appear: quiet rules, not grey boxes. */}
      <div className="mt-8 space-y-5" aria-hidden>
        {['Doctrine', 'Facts', 'Issue', 'Ruling'].map((title, i) => (
          <div key={title} className={percent > 20 + i * 18 ? 'opacity-100 transition-opacity duration-500' : 'opacity-30'}>
            <p className="text-sm font-semibold text-muted-foreground">{title}</p>
            <div className="mt-2 h-px w-full bg-border" />
            <div className="mt-2 h-px w-4/5 bg-border" />
          </div>
        ))}
      </div>
    </div>
  )
}
