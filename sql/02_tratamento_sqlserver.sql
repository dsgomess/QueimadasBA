
CREATE OR ALTER VIEW vw_queimadas_tratadas AS
SELECT 
    DataHora,
    
    -- Dimensão de tempo
    YEAR(DataHora) AS Ano,
    MONTH(DataHora) AS Mes,
    DAY(DataHora) AS Dia,
    
    Satelite,
    Pais,
    Estado,
    Municipio,
    Bioma,

    -- Tratamento de dados
    CASE 
        WHEN DiaSemChuva = -999 THEN NULL
        ELSE DiaSemChuva
    END AS DiaSemChuva,

    CASE 
        WHEN Precipitacao = -999 THEN NULL
        ELSE Precipitacao
    END AS Precipitacao,

    CASE 
        WHEN RiscoFogo = -999 THEN NULL
        ELSE RiscoFogo
    END AS RiscoFogo,

    CASE 
        WHEN FRP = -999 THEN NULL
        ELSE FRP
    END AS FRP,

    Latitude,
    Longitude

FROM vw_queimadas_unificadas;
