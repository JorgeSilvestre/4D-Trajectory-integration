import datetime
from pathlib import Path

import pandas as pd

from . import paths

# TODO Reflejar de alguna forma el estado de la trayectoria o las transformaciones aplicadas

# @dataclass
class Trajectory():
    attribute_list = (
        'ifplId',
        'callsign',
        'icao24',
        'aerodromeOfDeparture',
        'aerodromeOfDestination',
        'date',
        'airline',
        'estimatedTakeOffTime',
        'estimatedTimeOfArrival',
        'actualTakeOffTime',
        'actualTimeOfArrival',
        'flightState',
        'trajectory_state',
        'max_tma_rotation',
        'loop',
        'holding',
        'missing_start',
        'missing_end',
        'data_source_surveillance',
        'data_source_flights',
        'trajectory_stage',
        'first_state_dt',
        'last_state_dt',
        'num_vectors',
        'total_length',
    )

    def __init__(self, trajectory_id: str, date: str|datetime.date,
                 trajectory_state:str ='raw',
                 demo_folder: bool=None):
        # Static
        self.ifplId: str
        self.callsign: str
        self.icao24: str
        self.aerodromeOfDeparture: str
        self.aerodromeOfDestination: str
        self.date: datetime.date
        self.airline: str
        self.estimatedTakeOffTime: datetime.datetime
        self.estimatedTimeOfArrival: datetime.datetime
        self.actualTakeOffTime: datetime.datetime
        self.actualTimeOfArrival: datetime.datetime
        self.flightState: str
        # Description
        self.trajectory_state: str
        self.max_tma_rotation: float
        self.loop: bool
        self.holding: bool
        self.missing_start: bool
        self.missing_end: bool
        # Process description
        self.data_source_surveillance: str
        self.data_source_flights: str
        self.trajectory_stage: str
        # Calculated
        self.first_state_dt: datetime.datetime
        self.last_state_dt: datetime.datetime
        self.num_vectors: int
        self.total_length: float
        # Positions
        self.state_vectors: pd.DataFrame

        # TODO: Integrate weather data in the Trajectory class

        if trajectory_state == 'raw':
            folder = paths.NM_TRAJECTORIES_RAW_PATH / f'flightDate={date}'
        elif trajectory_state == 'clean':
            folder = paths.NM_TRAJECTORIES_PATH / f'flightDate={date}'
        elif trajectory_state == 'demo':
            folder = Path(demo_folder)

        self.state_vectors = pd.read_parquet(
            folder /  f'vectors.{date}.parquet',
            engine='pyarrow', dtype_backend='pyarrow',
            filters=[('ifplId', '==', trajectory_id)])

        metadata = pd.read_parquet(
            folder /  f'flights.{date}.parquet',
            engine='pyarrow', dtype_backend='pyarrow',
            filters=[('ifplId', '==', trajectory_id)]).iloc[0].to_dict()

        for k, v in metadata.items():
            setattr(self, k, v)