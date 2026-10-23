CREATE OR ALTER VIEW vw_queimadas_unificadas AS
SELECT * FROM bdqueimadas_2019 UNION ALL
SELECT * FROM bdqueimadas_2020 UNION ALL
SELECT * FROM bdqueimadas_2021 UNION ALL
SELECT * FROM bdqueimadas_2022 UNION ALL
SELECT * FROM bdqueimadas_2023 UNION ALL
SELECT * FROM bdqueimadas_2024 UNION ALL
SELECT * FROM bdqueimadas_2025;
GO

select * from vw_queimadas_unificadas
