type SectionPageProps = {
  eyebrow: string;
  title: string;
  description: string;
  bullets: string[];
};

export function SectionPage({ eyebrow, title, description, bullets }: SectionPageProps) {
  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 sm:p-8">
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{eyebrow}</p>
        <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">{title}</h2>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">
          {description}
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {bullets.map((item, index) => (
          <article
            key={item}
            className="rounded-[1.75rem] border border-white/10 bg-slate-950/45 p-5"
          >
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
              Placeholder {index + 1}
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-200">{item}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
