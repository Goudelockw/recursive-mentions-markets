-- Cost report: every table and materialized view in the database with its size and how often
-- it has been read since statistics were last reset. Read-only.
select n.nspname                                   as schema_name,
       c.relname                                   as name,
       case c.relkind when 'm' then 'matview' else 'table' end as kind,
       pg_total_relation_size(c.oid)               as bytes,
       coalesce(s.seq_scan, 0) + coalesce(s.idx_scan, 0) as reads,
       s.n_live_tup                                as live_rows,
       greatest(s.last_analyze, s.last_autoanalyze) as last_analyzed
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_stat_all_tables s on s.relid = c.oid
where c.relkind in ('r', 'm')
  and n.nspname not in ('pg_catalog', 'information_schema', 'pg_toast')
order by pg_total_relation_size(c.oid) desc;
