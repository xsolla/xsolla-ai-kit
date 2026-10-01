import { useEffect, useState } from 'react';
import { config } from '../config';

type QuestReward = {
  name: string | null;
  description: string | null;
  image_url: string | null;
  quantity: number;
  type: string;
};

type Quest = {
  id: string;
  name: string;
  description?: string | null;
  rewards: QuestReward[];
};

type PublicQuestList = { data: Quest[] };

function safeImageUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
}

function isQuestList(value: unknown): value is PublicQuestList {
  if (!value || typeof value !== 'object' || !('data' in value) || !Array.isArray(value.data)) return false;
  return value.data.every((quest) => Boolean(
    quest && typeof quest === 'object' &&
    typeof quest.id === 'string' && typeof quest.name === 'string' &&
    (quest.description == null || typeof quest.description === 'string') &&
    Array.isArray(quest.rewards) && quest.rewards.every((reward: QuestReward) =>
      reward && (reward.name == null || typeof reward.name === 'string') &&
      (reward.description == null || typeof reward.description === 'string') &&
      (reward.image_url == null || typeof reward.image_url === 'string') &&
      Number.isInteger(reward.quantity) && typeof reward.type === 'string',
    ),
  ));
}

function RewardRow({ reward }: { reward: QuestReward }) {
  const image = safeImageUrl(reward.image_url);
  const [imageFailed, setImageFailed] = useState(false);
  return (
    <div className="quest-reward">
      {image && !imageFailed ? (
        <img
          className="quest-reward__image"
          src={image}
          alt={reward.name ?? ''}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setImageFailed(true)}
        />
      ) : <div className="quest-reward__placeholder" aria-hidden="true">✦</div>}
      <div className="quest-reward__copy">
        <strong>{reward.name || 'Quest reward'}</strong>
        {reward.description && <p>{reward.description}</p>}
      </div>
      <span className="quest-reward__quantity">×{reward.quantity}</span>
      <span className="quest-reward__type">{reward.type.replaceAll('_', ' ')}</span>
    </div>
  );
}

export function XsollaQuestModule() {
  const [quests, setQuests] = useState<Quest[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!config.questListUrl) {
      setFailed(true);
      return;
    }

    const controller = new AbortController();
    fetch(config.questListUrl, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      credentials: 'omit',
    })
      .then((response) => {
        if (!response.ok) throw new Error(`Quest list request failed (${response.status})`);
        return response.json() as Promise<unknown>;
      })
      .then((body) => {
        if (!isQuestList(body)) throw new Error('Quest list response is invalid');
        setQuests(body.data);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setFailed(true);
      });

    return () => controller.abort();
  }, []);

  return (
    <section className="quest-module" data-xsolla-quest-module="1" aria-label="Quests">
      <div className="quest-module__heading">
        <p className="quest-module__eyebrow">Voidwall operations</p>
        <h2>Quests</h2>
        <p className="quest-module__disclaimer">
          Quests are configured by the publisher. Rewards are delivered to your Backpack.
        </p>
      </div>

      {quests === null && !failed && <p className="quest-module__state" role="status" aria-live="polite">Loading quests...</p>}
      {failed && <p className="quest-module__state" role="status">Quests are temporarily unavailable.</p>}
      {quests?.length === 0 && <p className="quest-module__state">No active quests right now.</p>}
      {quests && quests.length > 0 && (
        <div className="quest-module__grid">
          {quests.map((quest) => (
            <article className="quest-card" key={quest.id} data-quest-id={quest.id}>
              <div className="quest-card__copy">
                <h3>{quest.name}</h3>
                {quest.description && <p>{quest.description}</p>}
              </div>
              {quest.rewards.length > 0 && (
                <div className="quest-card__rewards" aria-label="Rewards">
                  {quest.rewards.map((reward, index) => <RewardRow key={`${quest.id}-${index}`} reward={reward} />)}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
