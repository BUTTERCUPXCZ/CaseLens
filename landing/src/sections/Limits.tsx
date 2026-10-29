import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { limitsCopy } from '@/copy'
import { stagger } from '@/lib/useReveal'
import { Cell, Chapter, RuledGrid } from '@/sections/Chapter'

/** What CaseLens does not do, said plainly, and the questions students ask first. */
export function Limits() {
  return (
    <Chapter id="limits" title={limitsCopy.title} lead={limitsCopy.lead}>
      <RuledGrid className="lg:grid-cols-2">
        <Cell data-reveal className="lg:border-r">
        <ul>
          {limitsCopy.items.map((item) => (
            <li key={item} className="border-b border-border py-4 text-base leading-relaxed first:pt-0 last:border-b-0 last:pb-0">
              {item}
            </li>
          ))}
        </ul>
        </Cell>
        <Cell data-reveal style={stagger(1)}>
          <h3 className="text-lg font-semibold">{limitsCopy.faqTitle}</h3>
          <Accordion type="single" collapsible className="mt-3">
            {limitsCopy.faq.map((item) => (
              <AccordionItem key={item.q} value={item.q}>
                <AccordionTrigger className="text-base">{item.q}</AccordionTrigger>
                <AccordionContent className="text-base leading-relaxed text-muted-foreground">{item.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </Cell>
      </RuledGrid>
    </Chapter>
  )
}
