import React from 'react';

function TransitionTimeline({ events, replayIndex, onReplayChange }) {
  const maxIndex = Math.max(events.length - 1, 0);
  const activeEvent = events[replayIndex] || null;

  return (
    <section className="twin-panel twin-timeline-panel">
      <div className="twin-panel-header">
        <div>
          <p className="twin-kicker">Replay Timeline</p>
          <h2>Run playback</h2>
        </div>
        <div className="twin-status-badge">
          <span>{activeEvent?.event_type || 'No replay frame selected'}</span>
        </div>
      </div>

      {events.length > 0 ? (
        <>
          <input
            type="range"
            min="0"
            max={maxIndex}
            value={Math.min(replayIndex, maxIndex)}
            onChange={(event) => onReplayChange(Number(event.target.value))}
            className="twin-range"
          />
          <div className="twin-timeline-markers">
            {events.map((event, index) => (
              <button
                key={event.event_id}
                type="button"
                className={`twin-timeline-chip ${index === replayIndex ? 'is-active' : ''}`}
                onClick={() => onReplayChange(index)}
              >
                <span>{index + 1}</span>
                <strong>{event.event_type}</strong>
                <small>{event.created_at}</small>
              </button>
            ))}
          </div>
        </>
      ) : (
        <p className="twin-empty">Run the chain or step through it to populate replay frames.</p>
      )}
    </section>
  );
}

export default TransitionTimeline;
