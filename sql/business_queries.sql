-- Day 15: SQL Business Queries
-- Uses viewing_records (or joined viewer_sessions + viewer_retention)

-- ============================================================================
-- QUERY 1: Content with Highest Retention
-- Aggregates viewer count, average completion, watch duration, pauses, and retention rate per title
-- ============================================================================
-- name: content_highest_retention
SELECT 
    content_id,
    COUNT(DISTINCT user_id) AS viewer_count,
    ROUND(AVG(completion_rate), 2) AS avg_completion_rate,
    ROUND(AVG(watch_duration), 2) AS avg_watch_duration,
    ROUND(AVG(pause_count), 2) AS avg_pause_count,
    ROUND(AVG(sessions_per_week), 2) AS avg_sessions_per_week,
    ROUND(AVG(CAST(retained AS REAL)), 4) AS retention_rate
FROM viewing_records
GROUP BY content_id
ORDER BY retention_rate DESC, viewer_count DESC;

-- ============================================================================
-- QUERY 2: Segment Summaries
-- Categorizes viewers by engagement thresholds and calculates segment performance
-- Thresholds:
-- Highly Engaged: completion_rate >= 80 AND sessions_per_week >= 5
-- At Risk / Low Engagement: completion_rate < 50 OR sessions_per_week <= 2
-- Moderately Engaged: remaining
-- ============================================================================
-- name: segment_summaries
WITH classified_viewers AS (
    SELECT
        user_id,
        completion_rate,
        watch_duration,
        pause_count,
        sessions_per_week,
        retained,
        CASE
            WHEN completion_rate >= 80.0 AND sessions_per_week >= 5 THEN 'Highly Engaged'
            WHEN completion_rate < 50.0 OR sessions_per_week <= 2 THEN 'At Risk / Low Engagement'
            ELSE 'Moderately Engaged'
        END AS segment
    FROM viewing_records
),
total_count AS (
    SELECT COUNT(*) AS total FROM classified_viewers
)
SELECT 
    c.segment,
    COUNT(*) AS viewer_count,
    ROUND((CAST(COUNT(*) AS REAL) / (SELECT total FROM total_count)) * 100.0, 2) AS viewer_pct,
    ROUND(AVG(c.completion_rate), 2) AS avg_completion_rate,
    ROUND(AVG(c.watch_duration), 2) AS avg_watch_duration,
    ROUND(AVG(c.pause_count), 2) AS avg_pause_count,
    ROUND(AVG(c.sessions_per_week), 2) AS avg_sessions_per_week,
    ROUND(AVG(CAST(c.retained AS REAL)), 4) AS retention_rate
FROM classified_viewers c
GROUP BY c.segment
ORDER BY 
    CASE c.segment
        WHEN 'Highly Engaged' THEN 1
        WHEN 'Moderately Engaged' THEN 2
        ELSE 3
    END;

-- ============================================================================
-- QUERY 3: Funnel Steps Analysis
-- Progression through the 6 viewing stages: Started -> 25% -> 50% -> 75% -> Finished -> Retained
-- ============================================================================
-- name: funnel_steps
WITH stage_counts AS (
    SELECT
        COUNT(*) AS total_records,
        SUM(CASE WHEN completion_rate > 0 THEN 1 ELSE 0 END) AS started_count,
        SUM(CASE WHEN completion_rate >= 25.0 THEN 1 ELSE 0 END) AS watched_25_count,
        SUM(CASE WHEN completion_rate >= 50.0 THEN 1 ELSE 0 END) AS watched_50_count,
        SUM(CASE WHEN completion_rate >= 75.0 THEN 1 ELSE 0 END) AS watched_75_count,
        SUM(CASE WHEN completion_rate >= 90.0 OR finished = 1 THEN 1 ELSE 0 END) AS finished_count,
        SUM(CASE WHEN retained = 1 THEN 1 ELSE 0 END) AS retained_count
    FROM viewing_records
)
SELECT 'Started' AS stage, started_count AS count, 100.0 AS pct_of_initial FROM stage_counts
UNION ALL
SELECT '25% watched', watched_25_count, ROUND((CAST(watched_25_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT '50% watched', watched_50_count, ROUND((CAST(watched_50_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT '75% watched', watched_75_count, ROUND((CAST(watched_75_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT 'Finished', finished_count, ROUND((CAST(finished_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT 'Retained', retained_count, ROUND((CAST(retained_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts;
