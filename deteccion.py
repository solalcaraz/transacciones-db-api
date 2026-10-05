import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

# ---- DETECCIÓN DE ANOMALÍAS CON IA ----
# Se combinan tres modelos no supervisados (Isolation Forest, LOF y K-Means) y se exige
# que al menos dos coincidan, para reducir los falsos positivos de cada modelo por separado.

FEATURES_CLIENTES = [
    "conteo_transacciones",
    "monto_promedio",
    "monto_std",
    "monto_maximo",
    "monto_minimo",
    "tiempo_entre_transacciones",
]

FEATURES_TRANSACCIONES = [
    "monto",
    "hora_del_dia",
    "es_fin_de_semana",
    "es_horario_nocturno",
    "tiempo_desde_ultima",
    "transacciones_cliente",
]


def transacciones_a_df(transacciones):
    df = pd.DataFrame([
        {
            "id": t.id,
            "id_cliente": t.id_cliente,
            "id_cajero": t.id_cajero,
            "id_tipo_transaccion": t.id_tipo_transaccion,
            "monto": float(t.monto),
            "fecha_hora": t.fecha_hora,
        }
        for t in transacciones
    ])
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def calcular_features_clientes(df):
    features = df.groupby("id_cliente").agg(
        conteo_transacciones=("monto", "count"),
        monto_promedio=("monto", "mean"),
        monto_std=("monto", "std"),
        monto_maximo=("monto", "max"),
        monto_minimo=("monto", "min"),
        tiempo_entre_transacciones=("fecha_hora", lambda x: x.diff().dt.total_seconds().mean()),
    ).reset_index()
    # Un cliente con una sola transacción no tiene desvío ni tiempo entre transacciones.
    return features.fillna(0)


# ---- CLIENTES ----

def detectar_clientes_sospechosos(df):
    """Devuelve una lista de (id_cliente, motivos) de los clientes marcados por al menos 2 de los 3 modelos."""
    features = calcular_features_clientes(df)
    X = features[FEATURES_CLIENTES]

    features["outlier_iso_forest"] = IsolationForest(contamination=0.05, random_state=42).fit_predict(X)
    features["outlier_lof"] = LocalOutlierFactor(n_neighbors=20, contamination="auto").fit_predict(X)

    # K-Means es sensible a la escala, así que solo este modelo trabaja con los datos escalados.
    X_scaled = StandardScaler().fit_transform(X)
    n_clusters = min(max(2, len(features) // 10), 10)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit(X_scaled)
    features["distancia_centroide"] = np.min(
        np.linalg.norm(X_scaled[:, np.newaxis] - kmeans.cluster_centers_, axis=2),
        axis=1,
    )
    # K-Means no detecta outliers por sí solo: se toma como anómalo al 5 % más alejado de su centroide.
    umbral_distancia = np.percentile(features["distancia_centroide"], 95)
    features["outlier_kmeans"] = np.where(features["distancia_centroide"] > umbral_distancia, -1, 1)

    votos = (
        (features["outlier_iso_forest"] == -1).astype(int)
        + (features["outlier_lof"] == -1).astype(int)
        + (features["outlier_kmeans"] == -1).astype(int)
    )
    sospechosos = features[votos >= 2]

    conteo_promedio = features["conteo_transacciones"].mean()
    tiempo_promedio = features["tiempo_entre_transacciones"].mean()

    resultados = []
    for _, row in sospechosos.iterrows():
        motivos = []
        if row["outlier_iso_forest"] == -1:
            motivos.append("Detectado por Isolation Forest (patrón anómalo)")
        if row["outlier_lof"] == -1:
            motivos.append("Detectado por LOF (outlier local)")
        if row["outlier_kmeans"] == -1:
            motivos.append("Detectado por K-Means (alejado de clusters normales)")

        # Los modelos no explican por qué marcan a alguien, así que se suman reglas
        # de negocio legibles para que un analista entienda la alerta.
        if row["monto_maximo"] > row["monto_promedio"] * 5:
            motivos.append("Monto muy alto comparado con su promedio")
        if row["conteo_transacciones"] > conteo_promedio * 3:
            motivos.append("Frecuencia inusual de transacciones")
        if row["tiempo_entre_transacciones"] < tiempo_promedio / 3:
            motivos.append("Transacciones demasiado seguidas")
        if row["distancia_centroide"] > umbral_distancia:
            motivos.append("Comportamiento alejado de patrones normales (clustering)")
        if not motivos:
            motivos.append("Comportamiento atípico indefinido")

        resultados.append((row["id_cliente"], motivos))
    return resultados


def clasificar_clientes_para_grafico(df):
    """Isolation Forest sobre dos features, para poder mostrar a los clientes en un gráfico 2D."""
    features = calcular_features_clientes(df)
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    features["sospechoso"] = iso_forest.fit_predict(features[["monto_promedio", "tiempo_entre_transacciones"]])
    return features


# ---- TRANSACCIONES ----

def _normalizar(col):
    return (col - col.min()) / (col.max() - col.min()) if col.max() != col.min() else 0


def detectar_anomalias_transacciones(df):
    """Agrega a df las marcas y el score de cada modelo, y devuelve (df, sospechosas)."""
    df["hora_del_dia"] = df["fecha_hora"].dt.hour
    df["dia_semana"] = df["fecha_hora"].dt.dayofweek
    df["es_fin_de_semana"] = df["dia_semana"].isin([5, 6]).astype(int)
    df["es_horario_nocturno"] = df["hora_del_dia"].between(0, 6).astype(int)

    df["monto_promedio_cliente"] = df.groupby("id_cliente")["monto"].transform("mean")
    df["monto_std_cliente"] = df.groupby("id_cliente")["monto"].transform("std")
    df["transacciones_cliente"] = df.groupby("id_cliente")["id"].transform("count")

    df = df.sort_values(["id_cliente", "fecha_hora"])
    df["tiempo_desde_ultima"] = df.groupby("id_cliente")["fecha_hora"].diff().dt.total_seconds().fillna(0)

    X_scaled = StandardScaler().fit_transform(df[FEATURES_TRANSACCIONES].fillna(0))

    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    df["outlier_iso_forest"] = iso_forest.fit_predict(X_scaled)
    df["score_iso_forest"] = iso_forest.score_samples(X_scaled)

    lof = LocalOutlierFactor(n_neighbors=20, contamination=0.1)
    df["outlier_lof"] = lof.fit_predict(X_scaled)
    df["score_lof"] = lof.negative_outlier_factor_

    # Con pocas transacciones (por ejemplo, las de un solo cliente) no se pueden armar 5 clusters.
    kmeans = KMeans(n_clusters=min(5, len(df)), random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X_scaled)
    distancias = np.linalg.norm(X_scaled - kmeans.cluster_centers_[df["cluster"]], axis=1)
    umbral_distancia = np.percentile(distancias, 90)
    df["outlier_kmeans"] = np.where(distancias > umbral_distancia, -1, 1)
    # Negativo para que los tres scores sigan la misma convención que sklearn: más bajo, más anómalo.
    df["score_kmeans"] = -distancias

    df["score_anomalia"] = (
        _normalizar(df["score_iso_forest"]) * 0.33
        + _normalizar(df["score_lof"]) * 0.33
        + _normalizar(df["score_kmeans"]) * 0.34
    )
    df["score_anomalia_100"] = df["score_anomalia"] * 100

    df["num_modelos_anomalos"] = (
        (df["outlier_iso_forest"] == -1).astype(int)
        + (df["outlier_lof"] == -1).astype(int)
        + (df["outlier_kmeans"] == -1).astype(int)
    )
    sospechosas = df[(df["num_modelos_anomalos"] >= 2) & (df["score_anomalia_100"] >= 50)]
    return df, sospechosas


def motivos_transaccion(row, monto_promedio, monto_std):
    motivos = []
    if row["outlier_iso_forest"] == -1:
        motivos.append("Detectado por Isolation Forest (patrón anómalo global)")
    if row["outlier_lof"] == -1:
        motivos.append("Detectado por LOF (outlier local)")
    if row["monto"] > monto_promedio + 3 * monto_std:
        motivos.append(f"Monto excesivamente alto (${row['monto']:.2f})")
    if row["monto_std_cliente"] > 0:
        z_score = (row["monto"] - row["monto_promedio_cliente"]) / row["monto_std_cliente"]
        if abs(z_score) > 3:
            motivos.append(f"Monto inusual para este cliente (Z-score: {z_score:.2f})")
    if row["es_horario_nocturno"] == 1 and row["monto"] > monto_promedio:
        motivos.append("Transacción de alto monto en horario nocturno")
    if 0 < row["tiempo_desde_ultima"] < 60:
        motivos.append(f"Transacción muy cercana a la anterior ({row['tiempo_desde_ultima']:.0f} segs)")
    if not motivos:
        motivos.append("Patrón atípico detectado (Alta anomalía, motivos no especificados)")
    return motivos
