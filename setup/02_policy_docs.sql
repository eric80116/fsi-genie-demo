CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.policy_docs AS
SELECT
  _metadata.file_name                                         AS filename,
  trim(regexp_replace(regexp_extract(value, '^#\\s*([^\\n]+)', 1), '\\r', '')) AS title,
  value                                                       AS content,
  size(split(trim(value), '\\s+'))                          AS word_count,
  length(value)                                               AS char_count
FROM read_files('/Volumes/{{catalog}}/{{schema}}/files/markdown/', format => 'text', wholeText => true, fileNamePattern => '*.md')
