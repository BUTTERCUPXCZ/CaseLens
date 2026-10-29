import { sampleCase } from '@/demo/sample'

/** The top of the app's case digest page: the case name in the case face, its citation in tabular figures. */
export function CaseHeader() {
  return (
    <header className="border-b border-border pb-4">
      <h3 className="font-serif text-lg leading-tight font-semibold @2xl:text-2xl">{sampleCase.name}</h3>
      <p className="tabular mt-1.5 text-sm text-muted-foreground">
        {sampleCase.number}, {sampleCase.decided} ({sampleCase.division}) · {sampleCase.ponente}
      </p>
    </header>
  )
}
