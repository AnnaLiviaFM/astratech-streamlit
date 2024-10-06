import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import ee
import geemap
import os
import cv2
import numpy as np
from PIL import Image
from skyfield.api import load, Topos, utc
from datetime import datetime, timedelta

# Inicialize a biblioteca do Earth Engine
ee.Initialize(project='ee-vitorgabrielnc')  # Substitua 'your-project-id' pelo seu ID de projeto real.

# Função para calcular o crédito de carbono
def calcular_credito_carbono(tipo_mata, tamanho_area):
    taxa_sequestro = {
        'mata atlântica': 15,
        'floresta amazônica': 12.5,
        'caatinga': 3.5,
        'cerrado': 3,
        'pantanal': 4
    }
    valor_por_bioma = {
        'mata atlântica': 7.5,
        'floresta amazônica': 12.5,
        'caatinga': 4.5,
        'cerrado': 6.5,
        'pantanal': 6.5
    }

    if tipo_mata not in taxa_sequestro:
        raise ValueError("Tipo de mata desconhecido.")
    
    credito_carbono = taxa_sequestro[tipo_mata] * tamanho_area * valor_por_bioma[tipo_mata]
    return credito_carbono

# Função para mostrar dados do Landsat
def mostrar_dados(longitude, latitude):
    # Define a região de interesse (um único ponto) usando as coordenadas do usuário
    region = ee.Geometry.Point([longitude, latitude])

    # Cria uma coleção de imagens do Landsat 8 com filtros
    collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                  .filterBounds(region)
                  .filter(ee.Filter.lt('CLOUD_COVER', 20))  # Ajuste a cobertura de nuvens
                  .sort('CLOUD'))

    # Pega a primeira imagem da coleção
    first_image = collection.first()
    
    if first_image is None:
        st.error("Nenhuma imagem disponível na coleção após a filtragem.")
        return  # Saia da função se não houver imagens

    # Extrai os valores de reflectância da superfície para todas as bandas na região selecionada
    bands = first_image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])

    # Amostra os valores dos pixels para a região especificada
    sample = bands.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=30
    ).getInfo()

    # Extrai os nomes das bandas e os valores de reflectância
    band_names = list(sample.keys())
    reflectance_values = list(sample.values())

    # Plota a assinatura espectral
    st.title("Assinatura Espectral na Localização do Ponto")
    plt.figure(figsize=(8, 6))
    plt.plot(band_names, reflectance_values, marker='o')
    plt.title('Assinatura Espectral na Localização do Ponto')
    plt.xlabel('Bandas do Landsat SR')
    plt.ylabel('Reflectância da Superfície')
    plt.grid(True)
    
    # Exibe o gráfico no Streamlit
    st.pyplot(plt)  # Exibe o gráfico gerado pelo matplotlib no Streamlit

def reflorestamento():
    st.title("Auxílio no Reflorestamento")

    # Título da seção
    st.title("Técnicas de Reflorestamento da AstraTech")

# Texto explicativo
    st.write(
    """
    Com o uso do satélite e dados da NASA, a AstraTech pode rapidamente localizar focos de incêndio e auxiliar os produtores que sofreram com desastres naturais. Entre as técnicas de reflorestamento, podemos citar:
    
    1. **Plantio de mudas**: plantar mudas de espécies em áreas degradadas em viveiros para posterior transporte para os locais onde ocorreu o desastre natural.
    
    2. **Semeadura aérea**: caso seja uma área muito grande ou de difícil acesso, pode-se realizar a dispersão das sementes por aviões agrícolas ou drones.
    
    3. **Nucleação**: esse método ocorre pela disseminação de sementes na área. Para isso, o lugar precisa estar ocupado pelas espécies responsáveis por essa disseminação. Por ser um processo mais natural, o reflorestamento pela nucleação costuma ser demorado e respeita os fatores de regeneração progressiva, iniciando com espécies pioneiras, como gramíneas e arbustos, passando por espécies intermediárias formadas por pequenas árvores, até chegar ao clímax, que representa a floresta totalmente evoluída.
    
    4. **Muvuca**: é feita através da mistura de diversas sementes com grãos e areia. Essa mistura é levada até a área que será reflorestada e é espalhada por todo o terreno. Com o tempo, várias espécies de plantas vão se desenvolvendo de maneira alternada e sem organização na área reflorestada.
    
    O reflorestamento traz diversas vantagens econômicas e sociais. Um dos principais avanços tecnológicos possibilitou o advento do crédito de carbono, que permite vender créditos sustentáveis para empresas e países que necessitam melhorar sua emissão de CO2.
    
    **Vantagens do Reflorestamento:**
    - Restabelecer a perda de biodiversidade nas regiões afetadas.
    - Reduzir o dióxido de carbono (CO2) no ar.
    - Reverter a erosão do solo de áreas pouco ou mais afetadas e preservar as bacias hidrográficas.
    - Cuidar da saúde e vida dos seres vivos.
    - Aumento dos nutrientes do solo.
    - Agem como aquedutos naturais, redistribuindo até 95% da água que absorvem.
    """
)

    
    # Função para ler coordenadas do usuário
    coordenadas_local = obter_coordenadas()  # Lê as coordenadas do usuário

    # Cálculo de crédito de carbono
    st.header("Cálculo de Crédito de Carbono")
    tipo_mata = st.selectbox("Escolha o tipo de bioma:", 
                              ['mata atlântica', 'floresta amazônica', 'caatinga', 'cerrado', 'pantanal'])
    tamanho_area = st.number_input("Digite o tamanho da área em hectares:", min_value=0.1, step=0.1)

    if st.button("Calcular Crédito de Carbono"):
        try:
            credito_carbono = calcular_credito_carbono(tipo_mata, tamanho_area)
            st.success(f"Crédito de carbono estimado anualmente (em dólares): US$ {credito_carbono:.2f}")
        except ValueError as e:
            st.error(str(e))

def calcular_passagem_landsat(coordenadas, dias=10):
    # Carrega dados da órbita dos satélites
    ts = load.timescale()

    # URL correta do TLE dos satélites Landsat
    tle_url = 'https://celestrak.com/NORAD/elements/resource.txt'
    satellites = load.tle_file(tle_url)

    # Procurando o satélite Landsat 8
    landsat8 = [sat for sat in satellites if 'LANDSAT 8' in sat.name][0]

    # Localização do ponto de interesse
    latitude, longitude = coordenadas
    localizacao = Topos(latitude_degrees=latitude, longitude_degrees=longitude)

    # Lista de passagens
    passagens = []

    # Verifica por um intervalo de 'dias'
    for i in range(dias):
        # Adiciona explicitamente o timezone UTC aos datetimes
        t0 = ts.utc(datetime.utcnow().replace(tzinfo=utc) + timedelta(days=i))
        t1 = ts.utc(datetime.utcnow().replace(tzinfo=utc) + timedelta(days=i + 1))

        # Calcula quando o satélite estará mais próximo da localização
        t, eventos = landsat8.find_events(localizacao, t0, t1, altitude_degrees=85.0)

        # Verifica se a passagem é ascendente ou descendente
        for ti, evento in zip(t, eventos):
            if evento == 0:  # Satélite subindo (rise)
                # Obtém a velocidade do satélite
                velocidade = landsat8.at(ti).velocity.km_per_s

                # Verifica o componente y da velocidade
                tipo_orbita = "Ascendente" if velocidade[1] < 0 else "Descendente"

                # Adiciona apenas passagens descendentes
                if tipo_orbita == "Descendente":
                    passagens.append((ti.utc_datetime(), tipo_orbita))

    return passagens

def venda_carbono():
    st.title("Venda de Crédito de Carbono")
    st.write("Você será direcionado para nosso marketplace...")
    st.markdown("[Acesse nosso marketplace](https://astratech.earth)")

# Menu de navegação
st.sidebar.title("Menu")
pagina = st.sidebar.selectbox("Selecione a página:", ["Dados Gerais", "Reflorestamento"])

# Função para ler coordenadas do usuário
def obter_coordenadas():
    latitude = st.number_input("Insira a latitude do ponto central:", -90.0, 90.0)
    longitude = st.number_input("Insira a longitude do ponto central:", -180.0, 180.0)
    return (latitude, longitude)

# Página principal com entrada de dados e botão para mostrar resultados
if pagina == "Dados Gerais":
    # Adicionando uma logo no canto superior
    st.image("/home/livs/Downloads/Logo2.png", width=500)  # Ajuste o caminho para sua logo
    # Título do aplicativo
    st.title("Análise de Dados Landsat")

    # Entradas do usuário
    lat = st.number_input("Insira a latitude do ponto central:", -90.0, 90.0)
    long = st.number_input("Insira a longitude do ponto central:", -180.0, 180.0)
    area = st.number_input("Área de abrangência (em km²):", min_value=1)

    # Botão para processar
    if st.button("Mostrar Dados"):
        st.title("Passagens do Landsat:")
        passagens = calcular_passagem_landsat((lat, long), dias=20)
        # Exibe as próximas passagens descendentes
        if passagens:
            st.write(f"Próximas passagens descendentes do Landsat 8 sobre o local (nos próximos 20 dias):")
            for passagem, tipo_orbita in passagens:
                st.write(f"{passagem} - Órbita: {tipo_orbita}")
        else:
            st.write("Nenhuma passagem descendente encontrada nos próximos dias.")

        # Mostrar dados da imagem Landsat
        mostrar_dados(long, lat)
        st.write("Você será direcionado para nosso Drive com as imagens de satélite das suas coordenadas...")
        st.markdown("[Acesse as imagens](https://drive.google.com/drive/folders/1PuDSznY6gh6cGEF5Cy6fD_e4PtTJXOiT?usp=sharing)")

# Página de Reflorestamento 
elif pagina == "Reflorestamento":
    reflorestamento()
