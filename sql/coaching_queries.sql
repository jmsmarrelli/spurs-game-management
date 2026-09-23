DROP VIEW IF EXISTS turnover_windows;
CREATE VIEW turnover_windows AS
SELECT kind, COUNT(*) AS turnovers, COUNT(DISTINCT game_id) AS games,
       AVG(allowed_8) AS points_8, AVG(allowed_12) AS points_12,
       AVG(allowed_16) AS points_16
FROM turnovers GROUP BY kind;

DROP VIEW IF EXISTS quarter_clock_groups;
CREATE VIEW quarter_clock_groups AS
SELECT clock_band, COUNT(*) AS quarters, AVG(return_attempt) AS return_rate,
       AVG(first_points) AS first_ppa, AVG(close_scored - close_allowed) AS closing_net
FROM quarter_attempts GROUP BY clock_band;

DROP VIEW IF EXISTS timeout_game_counts;
CREATE VIEW timeout_game_counts AS
WITH ordered AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY game_id, period ORDER BY seconds DESC, event_id
  ) AS decision_order
  FROM timeout_candidates
)
SELECT game_id, period, COUNT(*) AS candidates, SUM(treated) AS timeouts,
       MAX(decision_order) AS last_decision_order
FROM ordered GROUP BY game_id, period;
