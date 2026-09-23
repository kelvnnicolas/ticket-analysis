import pandas as pd

class DataCleaner:
    @staticmethod
    def clean_tickets(df: pd.DataFrame) -> pd.DataFrame:
        df_cleaned = df.copy()
        # Convert date columns to datetime safely
        df_cleaned['date_opened'] = pd.to_datetime(df_cleaned['date_opened'])
        df_cleaned['date_resolved'] = pd.to_datetime(df_cleaned['date_resolved'])
        
        # Identify resolved tickets for analytics
        df_cleaned['is_resolved'] = df_cleaned['status'].isin(['Resolved', 'Closed'])
        return df_cleaned
        
    @staticmethod
    def clean_history(df: pd.DataFrame) -> pd.DataFrame:
        df_cleaned = df.copy()
        df_cleaned['changed_at'] = pd.to_datetime(df_cleaned['changed_at'])
        return df_cleaned
