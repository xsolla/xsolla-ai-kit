import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/locales';
import { UI } from '../i18n/ui';
import { config } from '../config';
import { QUEST_COPY, fetchQuests, type Quest } from './api';

export type QuestState = { status: 'loading' } | { status: 'error' } | { status: 'ready'; quests: Quest[] };

export function QuestModuleView({ state, locale }: { state: QuestState; locale: Locale }) {
  const t = UI[locale];
  return (
    <section data-xsolla-quest-module="1" aria-label="Quests" className="quests">
      <p className="eyebrow">{t.questsEyebrow}</p>
      <h2>{t.questsTitle}</h2>
      <p className="xsolla-quest-disclaimer note">{QUEST_COPY.disclaimer}</p>
      {state.status === 'loading' && <p className="xsolla-quest-loading note" role="status" aria-live="polite">{QUEST_COPY.loading}</p>}
      {state.status === 'error' && <p className="xsolla-quest-error error">{QUEST_COPY.unavailable}</p>}
      {state.status === 'ready' && state.quests.length === 0 && <p className="xsolla-quest-empty note">{QUEST_COPY.empty}</p>}
      {state.status === 'ready' && state.quests.length > 0 && (
        <div className="quest-list">
          {state.quests.map((q) => (
            <article key={q.id} data-quest-id={q.id} className="quest-card">
              <h3>{q.name}</h3>
              {q.description && <p className="note">{q.description}</p>}
              <ul className="quest-rewards">
                {q.rewards.map((r, i) => (
                  <li key={i} className="quest-reward">
                    {r.imageUrl
                      ? <img src={r.imageUrl} alt={r.name ?? ''} loading="lazy" referrerPolicy="no-referrer" />
                      : <span className="quest-reward-media" aria-hidden="true" />}
                    <div>
                      {r.name && <strong>{r.name}</strong>}
                      {r.description && <p className="note">{r.description}</p>}
                    </div>
                    <span className="badge">x{r.quantity}</span>
                    {r.type && <span className="badge">{r.type}</span>}
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

export function XsollaQuestModule({ locale }: { locale: Locale }) {
  const [state, setState] = useState<QuestState>({ status: 'loading' });
  useEffect(() => {
    const ac = new AbortController();
    fetchQuests({ baseUrl: config.qpBaseUrl, merchantId: config.qpMerchantId, projectId: config.qpProjectId }, fetch, ac.signal)
      .then((quests) => setState({ status: 'ready', quests }))
      .catch(() => { if (!ac.signal.aborted) setState({ status: 'error' }); });
    return () => ac.abort();
  }, []);
  return <QuestModuleView state={state} locale={locale} />;
}
