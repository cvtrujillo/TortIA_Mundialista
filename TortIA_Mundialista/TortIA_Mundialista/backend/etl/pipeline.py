from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
import requests
from loguru import logger
from etl.sources.football_data import FootballDataSource
from etl.sources.fbref import FBrefSource
from etl.features import FeatureEngineer


class WorldCupETL:
    VENUE_ALTITUDE_M = {
        'Mexico City': 2240, 'Guadalajara': 1566, 'Monterrey': 538,
        'Dallas': 139, 'Los Angeles': 71, 'New York': 10,
        'Seattle': 20, 'San Francisco': 16, 'Boston': 9,
        'Miami': 2, 'Atlanta': 320, 'Kansas City': 304,
        'Toronto': 76, 'Vancouver': 70,
    }

    def __init__(self, football_data_token, rapidapi_key='', output_dir='data'):
        self.fd_source = FootballDataSource(token=football_data_token)
        self.fbref_source = FBrefSource()
        self.feature_engineer = FeatureEngineer()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def ingest_historical(self, date_from=None, date_to=None):
        competitions = ['PL', 'BL1', 'SA', 'FL1', 'PD', 'CL']
        seasons = ['2022', '2023', '2024']
        all_matches = []

        for comp in competitions:
            for season in seasons:
                df = self.fd_source.fetch_matches(comp, season)
                if not df.empty:
                    all_matches.append(df)
                    logger.info(f'  {comp}/{season}: {len(df)} partidos')

        if not all_matches:
            raise RuntimeError('No se pudo obtener ningun partido.')

        base_df = pd.concat(all_matches, ignore_index=True)
        base_df = base_df.drop_duplicates(subset=['match_id']).reset_index(drop=True)
        logger.info(f'Base dataset: {len(base_df)} partidos')

        base_df = self.fbref_source.enrich_with_xg(base_df)
        featured_df = self.feature_engineer.build(base_df)

        out_path = self.output_dir / 'matches_featured.parquet'
        featured_df.to_parquet(out_path, index=False)
        logger.success(f'Saved {len(featured_df)} rows -> {out_path}')
        return featured_df

    def ingest_live_result(self, match_id, home_goals, away_goals):
        logger.info(f'Live result: match={match_id} {home_goals}-{away_goals}')

    def get_venue_altitude(self, venue):
        return self.VENUE_ALTITUDE_M.get(venue, 50)
