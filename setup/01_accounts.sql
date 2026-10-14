CREATE OR REPLACE TABLE {{catalog}}.{{schema}}.accounts AS
SELECT * EXCEPT (_rescued_data)
FROM read_files('/Volumes/{{catalog}}/{{schema}}/files/csv/accounts.csv', format => 'csv', header => true, inferSchema => true, encoding => 'UTF-8')
