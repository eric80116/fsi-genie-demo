CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.loans AS
SELECT * EXCEPT (_rescued_data)
FROM read_files('/Volumes/{{catalog}}/{{schema}}/files/csv/loans.csv', format => 'csv', header => true, inferSchema => true, encoding => 'UTF-8')
