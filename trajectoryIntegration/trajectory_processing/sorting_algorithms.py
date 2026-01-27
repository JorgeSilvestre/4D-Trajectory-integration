import numpy as np
import pandas as pd

# Distance functions

def euclidean_distance(coords1, coords2):
    return np.sqrt(np.sum(np.power(coords2-coords1, 2), axis=1))

def haversine_distance(coords1, coords2, unit='mi'):
    # https://www.movable-type.co.uk/scripts/latlong.html
    coords1, coords2 = map(np.radians, [coords1, coords2])
    diff_lat = coords2[:,0] - coords1[:,0]
    diff_lon = coords2[:,1] - coords1[:,1]
    lat1, lat2 = coords1[:,0], coords2[:,0]
    
    a = np.sin(diff_lat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(diff_lon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    if unit=='mi':
        dist = 3959.87433 * c
    elif unit=='km':
        dist = 6372.8 * c
    
    # Altitude
    if coords1.shape[1] == 3 and coords2.shape[1] == 3:
        diff_alt = (coords2[:,2]-coords1[:,2])
        dist = np.sqrt(np.power(dist, 2)+np.power(diff_alt, 2))


    # if len(coords1)==3 and len(coords2)==3:
    #     alt1, alt2 = coords1[2], coords2[2]
    #     dist = np.sqrt(np.power(dist,2) + np.power((alt2-alt1)/5280, 2))

    return dist

def distance_matrix(positions, distance_function='euclidean'):
    if distance_function == 'euclidean':
        diffs = euclidean_distance(np.expand_dims(positions.transpose(),0), 
                                   np.expand_dims(positions,2))
    elif distance_function == 'haversine':
        diffs = haversine_distance(np.expand_dims(positions.transpose(),0), 
                                   np.expand_dims(positions,2))
    return diffs
    
    return np.sqrt(np.sum(np.power(np.expand_dims(positions,2)-np.expand_dims(positions.transpose(),0), 2), axis=1))

def path_length(positions, distance_function='haversine'):
    if distance_function == 'euclidean':
        diffs = euclidean_distance(positions[:-1], positions[1:])
        return np.sum(diffs, axis=0)
    elif distance_function == 'haversine':
        diffs = haversine_distance(positions[:-1], positions[1:])
        return np.sum(diffs, axis=0)

def haversine_cost_function(coords, thetas, unit='mi'):
    pass

def sort_by_distance_reference_point(df):
    pass

# Algorithms

def nearest_neighbours(df: pd.DataFrame, distance_function='haversine', **kwargs):
    df = df.copy()
    if 'old_index' not in df.columns:
        df = df.reset_index(drop=False).rename(columns={'index':'old_index'})
    array = df[['latitude','longitude']].to_numpy(dtype='float32')
    distances = distance_matrix(array, distance_function)

    # Starting from the first vector, closest vector is iteratively identified,
    # excluding those that were already visited
    order = [0]
    # Mask used to hide visited vectors
    mask = np.zeros(shape=array.shape[0]).astype(bool)
    mask[-1] = True
    for i in range(len(array)-2):
        mask[order[-1]] = True
        closest = np.ma.array(distances[order[-1]], mask=mask).argmin(fill_value=np.inf)
        order.append(closest)
    order.append(len(df)-1)

    return df.iloc[order]

def _generate_changes(start:int, end:int, skip:int = 1) -> list[tuple[int,int]]:
    '''
        Genera reemplazos de cada elemento con cada uno de los elementos siguientes
        (sin contar el inmediatamente siguiente) en base a sus índices correlativos
        en la secuencia (empezando en 0). Ignora el primer y último elementos.

        start
            Índice del primer elemento a considerar
        end
            Índice del último elemento a considerar
        skip
            Número de elementos al comienzo de la secuencia para los que no se generan cambios

    '''
    changes = [(v1,v2) for v1 in range(start+skip, end-start-2) for v2 in range(v1+1, end-start-1)]
    return changes

def opt2(df: pd.DataFrame, distance_function='haversine', **kwargs):
    df = df.copy()
    if 'old_index' not in df.columns:
        df = df.reset_index(drop=False).rename(columns={'index':'old_index'})
    array = df[['latitude','longitude']].to_numpy(dtype='float32')
    current_dist = path_length(array, distance_function)
    order = list(range(len(array)))

    changes = _generate_changes(0, len(array), 1)
    max_iteraciones = 100000
    for j in range(max_iteraciones):
        improvements = 0
        for i, (v1, v2) in enumerate(changes):
            candidate = np.concatenate([array[:v1],
                                        array[v2:v1-1:-1],
                                        array[v2+1:]])
            candidate_dist = path_length(candidate, distance_function)
            if candidate_dist < current_dist:
                array = candidate
                current_dist = candidate_dist
                order = order[:v1]+order[v2:v1-1:-1]+order[v2+1:]
                improvements = True
        if not improvements:
            break
    return df.iloc[order]

def opt2_reversed(df: pd.DataFrame, distance_function='haversine', **kwargs):
    df = df.copy()
    df = df.iloc[::-1]
    df = opt2(df.iloc[::-1], distance_function)
    df = df.iloc[::-1]

    return df

def _generate_windows(data_size:int, window_size:int, overlap:int, min_index:int=0, max_index:int=0) -> tuple[tuple[int,int,int]]:
    '''Genera ventanas deslizantes a partir del tamaño de una estructura tabular

    Genera índices para las ventanas deslizantes de tamaño window_size aplicadas
    sobre una estructura de datos de longitud data_size.

    Args:
        data_size: Longitud de la estructura de datos
        window_size: Tamaño de la ventana deslizante
        overlap: Número de elementos que se solapan entre ventanas consecutivas
        min_index: Índice a partir del cual se calculan las ventanas
        max_index: Índice hasta el que se generan las ventanas

    Returns:
        Un conjunto de tripletas (num. ventana, índice inicial, índice final)
    '''
    if max_index and max_index <= data_size: #
        data_size = max_index

    windows = []
    number_of_windows = ((data_size-min_index)//(window_size-overlap))+1
    for x in range(number_of_windows):
        window_min = x*(window_size-overlap) + min_index
        window_max = x*(window_size-overlap) + min_index + window_size
        window_max = window_max if window_max <= data_size else data_size
        windows.append((x, window_min, window_max))
        if window_max == data_size:
            break

    return windows

def opt2_progressive(df: pd.DataFrame, window_size:int, overlap:int, distance_function='haversine', **kwargs):
    df = df.copy()
    if 'old_index' not in df.columns:
        df = df.reset_index(drop=False).rename(columns={'index':'old_index'})
    windows = _generate_windows(len(df), window_size, overlap)
    for it, start, end in windows:
        df.iloc[start:end] = opt2(df.iloc[start:end], distance_function)
    return df

def opt2_progressive_reversed(df: pd.DataFrame, window_size:int, overlap:int, distance_function='haversine', **kwargs):
    df = df.copy()
    df = df.iloc[::-1]
    df = opt2_progressive(df.iloc[::-1], window_size, overlap, distance_function)
    df = df.iloc[::-1]

    return df

def opt2_restricted(df: pd.DataFrame, n_closest=10, distance_function='haversine', **kwargs):
    df = df.copy()
    if 'old_index' not in df.columns:
        df = df.reset_index(drop=False).rename(columns={'index':'old_index'})
    array = df[['latitude','longitude']].to_numpy(dtype='float32')
    current_dist = path_length(array, distance_function)
    order = df.index.to_list()

    changes = _generate_changes(0, len(array), 1)
    max_iteraciones = 100000
    for j in range(max_iteraciones):
        distances = distance_matrix(array, distance_function)
        mask = np.zeros(shape=df.shape[0]).astype(bool)
        mask[0] = True
        closest = {}
        for i in range(0, len(df)-n_closest-1):
            mask[i] = True
            nclosest = np.ma.array(distances[i], mask=mask).argsort()[:n_closest]
            closest[i] = set(nclosest)
        changes_it = [(v1, v2) for (v1,v2) in changes if (v1 in closest and v2 in closest[v1]) or v1 not in closest]
        
        improvements = 0
        for i, (v1, v2) in enumerate(changes_it):
            candidate = np.concatenate([array[:v1],
                                        array[v2:v1-1:-1],
                                        array[v2+1:]])
            candidate_dist = path_length(candidate, distance_function)
            if candidate_dist < current_dist:
                array = candidate
                current_dist = candidate_dist
                order = order[:v1]+order[v2:v1-1:-1]+order[v2+1:]
                improvements = True
        if not improvements:
            break
    return df.iloc[order]

def opt2_b(df: pd.DataFrame):
    df = df.copy()
    # Sorprendentemente, más lento
    max_iteraciones = 100000
    changes = [(v1,v2) for v1 in range(1,len(df)-1) for v2 in range(v1+2, len(df)-1)]
    array = df[['latitude','longitude']].to_numpy()
    order = df.index.to_list()
    for j in range(max_iteraciones):
        improvements = 0
        for i, (v1, v2) in enumerate(changes):
            current_dist = euclidean_distance(array[v1-1], array[v1]) + euclidean_distance(array[v2+1], array[v2])
            candidate_dist = euclidean_distance(array[v1-1], array[v2]) + euclidean_distance(array[v1], array[v2+1])
            if candidate_dist < current_dist:
                improvements += 1
                array = np.concatenate([array[:v1],
                                        array[v2:v1-1:-1],
                                        array[v2+1:]])
                order = order[:v1]+order[v2:v1-1:-1]+order[v2+1:]
        if not improvements:
            break
    
    return df.iloc[order]