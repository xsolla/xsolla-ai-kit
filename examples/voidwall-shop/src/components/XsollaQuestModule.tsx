import { useEffect, useState } from 'react';
import { config } from '../config';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { QUEST_COPY, fetchQuests, type Quest } from '../quests/api';

type State = { status: 'loading' } | { status: 'error' } | { status: 'ready'; quests: Quest[] };

export function XsollaQuestModule({ locale }: { locale: Locale }) {
  const t = UI[locale];
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    const ctl = new AbortController();
    fetchQuests(config.quests, ctl.signal)
      .then((quests) => setState({ status: 'ready', quests }))
      .catch(() => { if (!ctl.signal.aborted) setState({ status: 'error' }); });
    return () => ctl.abort();
  }, []);

  return (
    <section id="quests" className="quests" data-xsolla-quest-module="1" aria-label="Quests">
      <p className="quests-eyebrow">{t.questsEyebrow}</p>
      <h2>{t.questsHeading}</h2>
      <p className="xsolla-quest-disclaimer note">{QUEST_COPY.disclaimer}</p>
      {state.status === 'loading' && <p className="xsolla-quest-loading" role="status" aria-live="polite">Loading quests...</p>}
      {state.status === 'error' && <p className="xsolla-quest-error error">{QUEST_COPY.error}</p>}
      {state.status === 'ready' && state.quests.length === 0 && <p className="xsolla-quest-empty">{QUEST_COPY.empty}</p>}
      {state.status === 'ready' && state.quests.length > 0 && (
        <div className="quest-list">
          {state.quests.map((q) => (
            <article key={q.id} data-quest-id={q.id} className="quest-card">
              <h3>{q.name}</h3>
              {q.description && <p>{q.description}</p>}
              <ul className="quest-rewards">
                {q.rewards.map((r, i) => (
                  <li key={i} className="quest-reward">
                    {r.imageUrl
                      ? <img src={r.imageUrl} alt={r.name ?? ''} loading="lazy" referrerPolicy="no-referrer" />
                      : <span className="quest-reward-media" aria-hidden="true" />}
                    <div>
                      {r.name && <strong>{r.name}</strong>}
                      {r.description && <p className="note">{r.description}</p>}
                      <span className="quest-badge">{`x${r.quantity}`}</span>
                      {r.type && <span className="quest-badge">{r.type}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
