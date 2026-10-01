import { useEffect, useState } from 'react';
import { config, questSource } from '../config';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { fetchQuests, type Quest } from '../quests/api';

// Fixed publisher-facing copy; intentionally not localized.
export const QUEST_DISCLAIMER = 'Quests are configured by the publisher. Rewards are delivered to your Backpack.';
export const QUEST_EMPTY = 'No active quests right now.';
export const QUEST_ERROR = 'Quests are temporarily unavailable.';

type State = { status: 'loading' } | { status: 'error' } | { status: 'ready'; quests: Quest[] };

export function XsollaQuestModule({ locale }: { locale: Locale }) {
  const t = UI[locale];
  const source = questSource(config);
  const [state, setState] = useState<State>(source ? { status: 'loading' } : { status: 'error' });

  useEffect(() => {
    if (!source) { setState({ status: 'error' }); return; }
    const ctl = new AbortController();
    setState({ status: 'loading' });
    fetchQuests(source, fetch, ctl.signal)
      .then((quests) => setState({ status: 'ready', quests }))
      .catch(() => { if (!ctl.signal.aborted) setState({ status: 'error' }); });
    return () => ctl.abort();
  }, [source?.baseUrl, source?.merchantId, source?.projectId]);

  return (
    <section data-xsolla-quest-module="1" aria-label="Quests" className="quests">
      <p className="quests-eyebrow">{t.questsEyebrow}</p>
      <h2>{t.questsTitle}</h2>
      <p className="note xsolla-quest-disclaimer">{QUEST_DISCLAIMER}</p>
      {state.status === 'loading' && <p className="xsolla-quest-loading note" role="status" aria-live="polite">{t.questsLoading}</p>}
      {state.status === 'error' && <p className="xsolla-quest-error error">{QUEST_ERROR}</p>}
      {state.status === 'ready' && state.quests.length === 0 && <p className="xsolla-quest-empty note">{QUEST_EMPTY}</p>}
      {state.status === 'ready' && state.quests.length > 0 && (
        <div className="quest-list">
          {state.quests.map((q) => (
            <article key={q.id} data-quest-id={q.id} className="quest-card">
              <h3>{q.name}</h3>
              {q.description && <p className="note">{q.description}</p>}
              {q.rewards.length > 0 && (
                <ul className="quest-rewards" aria-label={t.questsReward}>
                  {q.rewards.map((r, i) => (
                    <li key={i} className="quest-reward">
                      {r.imageUrl
                        ? <img src={r.imageUrl} alt={r.name ?? ''} loading="lazy" referrerPolicy="no-referrer" />
                        : <span className="quest-reward-placeholder" aria-hidden="true" />}
                      <div>
                        {r.name && <strong>{r.name}</strong>}
                        {r.description && <p className="note">{r.description}</p>}
                        <p className="quest-badges">
                          <span className="badge">×{r.quantity}</span>
                          <span className="badge">{r.type}</span>
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
