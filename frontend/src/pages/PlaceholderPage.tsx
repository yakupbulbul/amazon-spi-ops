type PlaceholderPageProps = {
  title: string;
};

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <section className="space-y-4">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Phase 1</p>
        <h2 className="text-3xl font-semibold text-white">{title}</h2>
      </div>
      <p className="max-w-2xl text-sm text-slate-400">
        This route is wired and ready for the production admin experience that will be expanded
        in the next commits.
      </p>
    </section>
  );
}

