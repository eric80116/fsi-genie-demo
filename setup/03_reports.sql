CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.reports AS
WITH parsed AS (
  SELECT regexp_extract(path, '[^/]+$', 0) AS filename,
         ai_parse_document(content) AS doc
  FROM read_files('/Volumes/{{catalog}}/{{schema}}/files/pdf/', format => 'binaryFile', fileNamePattern => '*.pdf')
)
SELECT
  filename,
  array_join(
    transform(try_cast(doc:document:elements AS ARRAY<VARIANT>), e -> try_cast(e:content AS STRING)),
    '\n') AS full_text
FROM parsed
-- branch_npl_risk_analysis_2024q3.pdf is reserved for the live file-attachment demo (Type D)
WHERE filename <> 'branch_npl_risk_analysis_2024q3.pdf'
