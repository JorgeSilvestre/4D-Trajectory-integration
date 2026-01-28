from .. import params, paths
from ..trajectory import Trajectory
from ..utils import haversine_np, haversine_np_track

def fill_missing_data(trajectory: Trajectory) -> Trajectory:
    # trajectory.vectors = trajectory.vectors.drop_duplicates()

    return trajectory

def resolve_position_outliers():
    pass
