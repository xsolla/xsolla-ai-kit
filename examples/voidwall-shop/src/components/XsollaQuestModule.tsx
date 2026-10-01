import { useEffect, useState } from 'react';
import { config } from '../config';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { fetchQuests, type Quest } from '../quests/api';

const DISCLAIMER = 'Quests are configured by the publisher. Rewards are delivered to your Backpack.';
const EMPTY = 'No active quests right now.';
const UNAVAILABLE = 'Quests are temporarily unavailable.';

type State = { status: 'loading' } | { status: 'error' } | { status: 'ready'; quests: Quest[] };

export function XsollaQuestModule({ locale }: { locale: Locale }) {
  const t = UI[locale];
  const configured = Boolean(config.merchantId && config.projectId);
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    if (!configured) return;
    let live = true;
    fetchQuests(config.merchantId, config.projectId, config.questsBaseUrl)
      .then((quests) => live && setState({ status: 'ready', quests }))
      .catch(() => live && setState({ status: 'error' }));
    return () => { live = false; };
  }, [configured]);

  if (!configured) return null;

  return (
    <section data-xsolla-quest-module="1" aria-label="Quests" className="quests">
      <p className="quests-eyebrow">{t.questsEyebrow}</p>
      <h2>{t.questsHeading}</h2>
      <p className="xsolla-quest-disclaimer note">{DISCLAIMER}</p>
      {state.status === 'loading' && <p className="xsolla-quest-loading" role="status" aria-live="polite">{t.questsLoading}</p>}
      {state.status === 'error' && <p className="xsolla-quest-error note">{UNAVAILABLE}</p>}
      {state.status === 'ready' && state.quests.length === 0 && <p className="xsolla-quest-empty note">{EMPTY}</p>}
      {state.status === 'ready' && state.quests.length > 0 && (
        <div className="quest-list">
          {state.quests.map((q) => (
            <article key={q.id} data-quest-id={q.id} className="quest-card">
              <h3>{q.name}</h3>
              {q.description && <p>{q.description}</p>}
              {q.rewards.map((r, i) => (
                <div key={i} className="quest-reward">
                  {r.imageUrl
                    ? <img src={r.imageUrl} alt={r.name ?? ''} loading="lazy" referrerPolicy="no-referrer" />
                    : <div className="quest-reward-media" aria-hidden="true" />}
                  <div className="quest-reward-body">
                    {r.name && <strong>{r.name}</strong>}
                    {r.description && <span className="note">{r.description}</span>}
                    <span className="quest-badges">
                      <span className="quest-badge">&times;{r.quantity}</span>
                      {r.type && <span className="quest-badge">{r.type}</span>}
                    </span>
                  </div>
                </div>
              ))}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
