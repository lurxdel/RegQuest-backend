import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from django.utils import timezone
from .models import Request
from django.db.models.functions import TruncWeek
from django.db.models import Count

def get_weekly_prediction(include_legacy=True):
    # 1. Fetch historical data (last 104 weeks to include 2025 legacy data)
    now = timezone.now()
    start_date = now - timedelta(weeks=104)
    
    queryset = Request.objects.filter(created_at__gte=start_date)
    if not include_legacy:
        queryset = queryset.exclude(tracking_number__startswith="LEGACY-")

    qs = (
        queryset
        .annotate(week=TruncWeek('created_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )
    
    if len(qs) < 3:
        return {
            'predicted_volume': 0,
            'trend_percentage': 0,
            'trend_direction': 'neutral',
            'message': 'Not enough historical data to generate an ML prediction.'
        }
        
    df = pd.DataFrame(list(qs))
    
    # Fill missing weeks with 0
    df['week'] = pd.to_datetime(df['week'])
    df.set_index('week', inplace=True)
    # Resample to ensure every week has a row, filling gaps with 0
    df = df.resample('W').sum().fillna(0).reset_index()
    
    if len(df) < 3:
        return {
            'predicted_volume': 0,
            'trend_percentage': 0,
            'trend_direction': 'neutral',
            'message': 'Not enough historical weeks to generate an ML prediction.'
        }
        
    # 2. Prepare data for scikit-learn Linear Regression
    # X = Time index (0, 1, 2, ... N)
    # y = Request count for that week
    X = np.arange(len(df)).reshape(-1, 1)
    y = df['count'].values
    
    # 3. Train the model
    model = LinearRegression()
    model.fit(X, y)
    
    # 4. Predict the next week (N+1)
    next_week_index = np.array([[len(df)]])
    predicted_val = model.predict(next_week_index)[0]
    
    # Ensure prediction isn't negative
    predicted_val = max(0, int(round(predicted_val)))
    
    # 5. Calculate Trend vs Last Week
    last_week_count = y[-1]
    
    if last_week_count == 0:
        trend_percentage = 100 if predicted_val > 0 else 0
    else:
        trend_percentage = ((predicted_val - last_week_count) / last_week_count) * 100
        
    trend_direction = 'up' if trend_percentage > 0 else 'down' if trend_percentage < 0 else 'neutral'
    
    return {
        'predicted_volume': predicted_val,
        'trend_percentage': round(abs(trend_percentage), 1),
        'trend_direction': trend_direction,
        'message': f"Based on historical trends, we predict {predicted_val} document requests next week."
    }

def predict_release_date(document_type_id):
    # 1. Fetch historical data (use all legacy completed requests)
    qs = Request.objects.filter(
        status='completed',
        processed_at__isnull=False,
        tracking_number__startswith="LEGACY-"
    ).values('document_type_id', 'created_at', 'processed_at')
    
    if len(qs) < 10:
        # Not enough data, return default 5 days
        return 5
        
    df = pd.DataFrame(list(qs))
    
    # Calculate processing time in days
    df['processing_days'] = (df['processed_at'] - df['created_at']).dt.days
    
    # Calculate requested day of week (0=Monday, 6=Sunday)
    df['weekday'] = df['created_at'].dt.dayofweek
    
    # We only care about predicting for THIS document_type_id
    doc_df = df[df['document_type_id'] == document_type_id]
    
    if len(doc_df) < 3:
        # Not enough data for this specific document, fallback to overall median
        return max(1, int(df['processing_days'].median()))
        
    # X = weekday, y = processing days
    X = doc_df[['weekday']].values
    y = doc_df['processing_days'].values
    
    # Simple linear regression (RandomForest/DecisionTree might overfit for just weekday)
    model = LinearRegression()
    model.fit(X, y)
    
    current_weekday = timezone.now().weekday()
    predicted_days = model.predict(np.array([[current_weekday]]))[0]
    
    return max(1, int(round(predicted_days)))
