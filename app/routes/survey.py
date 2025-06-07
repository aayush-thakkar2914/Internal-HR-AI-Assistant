"""
Survey and engagement API routes for the HR AI Assistant.

This module contains all survey-related endpoints including survey creation,
response collection, and engagement analytics.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional

from app.config.database import get_db
from app.models.employee import Employee
from app.models.survey import Survey, SurveyResponse, EngagementMetric, SurveyStatus
from app.schemas.survey import (
    SurveyCreate, SurveyUpdate, SurveyResponse as SurveyResponseSchema,
    SurveyResponseCreate, SurveyResponseUpdate, SurveyResponseData,
    EngagementMetricCreate, EngagementMetricResponse
)
from app.services.survey_service import survey_service
from app.services.notification_service import notification_service
from app.middleware.auth import get_current_active_user, require_role
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Survey Management Routes

@router.post("/", response_model=SurveyResponseSchema)
async def create_survey(
    survey_data: SurveyCreate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Create a new survey (HR only)
    
    Args:
        survey_data: Survey creation data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        SurveyResponseSchema: Created survey
    """
    try:
        survey = Survey(
            title=survey_data.title,
            description=survey_data.description,
            survey_type=survey_data.survey_type,
            instructions=survey_data.instructions,
            estimated_duration=survey_data.estimated_duration,
            is_anonymous=survey_data.is_anonymous,
            is_mandatory=survey_data.is_mandatory,
            start_date=survey_data.start_date,
            end_date=survey_data.end_date,
            allow_multiple_responses=survey_data.allow_multiple_responses,
            show_progress=survey_data.show_progress,
            randomize_questions=survey_data.randomize_questions,
            require_all_questions=survey_data.require_all_questions,
            created_by=current_user.id,
            status=SurveyStatus.DRAFT
        )
        
        # Set questions
        if survey_data.questions:
            survey.set_questions(survey_data.questions)
        
        # Set targeting
        if survey_data.target_departments:
            survey.target_departments = survey_data.target_departments
        if survey_data.target_roles:
            survey.target_roles = survey_data.target_roles
        if survey_data.target_employees:
            survey.target_employees = survey_data.target_employees
        
        db.add(survey)
        db.commit()
        db.refresh(survey)
        
        logger.info(f"Survey created: {survey.id} by {current_user.employee_id}")
        
        return SurveyResponseSchema.from_orm(survey)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create survey"
        )

@router.post("/templates/{template_name}", response_model=SurveyResponseSchema)
async def create_survey_from_template(
    template_name: str,
    customizations: Optional[Dict[str, Any]] = None,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Create survey from predefined template (HR only)
    
    Args:
        template_name: Name of template to use
        customizations: Custom modifications to template
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        SurveyResponseSchema: Created survey
    """
    try:
        success, survey, errors = survey_service.create_survey_from_template(
            db, current_user, template_name, customizations
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Survey creation failed: {', '.join(errors)}"
            )
        
        logger.info(f"Survey created from template '{template_name}': {survey.id}")
        
        return SurveyResponseSchema.from_orm(survey)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating survey from template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create survey from template"
        )

@router.get("/", response_model=List[SurveyResponseSchema])
async def get_surveys(
    status_filter: Optional[SurveyStatus] = Query(None),
    survey_type: Optional[str] = Query(None),
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get surveys with filtering
    
    Args:
        status_filter: Filter by survey status
        survey_type: Filter by survey type
        active_only: Show only currently active surveys
        skip: Number of surveys to skip
        limit: Maximum number of surveys to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[SurveyResponseSchema]: List of surveys
    """
    try:
        query = db.query(Survey)
        
        # Apply filters
        if status_filter:
            query = query.filter(Survey.status == status_filter)
        
        if survey_type:
            query = query.filter(Survey.survey_type == survey_type)
        
        if active_only:
            query = query.filter(Survey.status == SurveyStatus.ACTIVE)
        
        # For non-HR users, only show published/active surveys they can participate in
        if current_user.role.title.lower() not in ['hr', 'human resources']:
            query = query.filter(Survey.status.in_([SurveyStatus.ACTIVE]))
            
            # Add targeting filters (simplified)
            # In a real implementation, this would check department/role targeting
        
        # Apply pagination and ordering
        surveys = query.order_by(Survey.created_at.desc())\
                      .offset(skip).limit(limit).all()
        
        return [SurveyResponseSchema.from_orm(survey) for survey in surveys]
        
    except Exception as e:
        logger.error(f"Error retrieving surveys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve surveys"
        )

@router.get("/{survey_id}", response_model=SurveyResponseSchema)
async def get_survey(
    survey_id: int,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific survey by ID
    
    Args:
        survey_id: Survey ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        SurveyResponseSchema: Survey details
    """
    try:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        # Check access permissions
        if (current_user.role.title.lower() not in ['hr', 'human resources'] and
            survey.status not in [SurveyStatus.ACTIVE]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return SurveyResponseSchema.from_orm(survey)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve survey"
        )

@router.put("/{survey_id}", response_model=SurveyResponseSchema)
async def update_survey(
    survey_id: int,
    survey_update: SurveyUpdate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Update survey (HR only)
    
    Args:
        survey_id: Survey ID
        survey_update: Survey update data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        SurveyResponseSchema: Updated survey
    """
    try:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        # Check if survey can be modified
        if survey.status in [SurveyStatus.COMPLETED, SurveyStatus.ARCHIVED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Survey cannot be modified in current status"
            )
        
        # Update fields
        update_data = survey_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(survey, field):
                if field == "questions" and value:
                    survey.set_questions(value)
                else:
                    setattr(survey, field, value)
        
        survey.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(survey)
        
        logger.info(f"Survey updated: {survey.id} by {current_user.employee_id}")
        
        return SurveyResponseSchema.from_orm(survey)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update survey"
        )

@router.post("/{survey_id}/publish")
async def publish_survey(
    survey_id: int,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Publish survey and send invitations (HR only)
    
    Args:
        survey_id: Survey ID
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        Dict: Publication confirmation
    """
    try:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        if survey.status != SurveyStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft surveys can be published"
            )
        
        # Update survey status
        survey.status = SurveyStatus.ACTIVE
        survey.published_at = datetime.utcnow()
        
        # Calculate total invited (simplified)
        if survey.target_employees:
            survey.total_invited = len(survey.target_employees)
        else:
            # Count all active employees (simplified targeting)
            survey.total_invited = db.query(Employee).filter(Employee.is_active == True).count()
        
        db.commit()
        
        # Send survey invitations (this would be done asynchronously in production)
        try:
            # Get target employees
            target_employees = db.query(Employee).filter(Employee.is_active == True).all()
            
            # Send invitations
            survey_data = {
                "title": survey.title,
                "description": survey.description,
                "estimated_duration": survey.estimated_duration,
                "deadline": survey.end_date.strftime("%B %d, %Y") if survey.end_date else "",
                "is_anonymous": survey.is_anonymous,
                "link": f"/surveys/{survey.id}/respond"  # This would be the actual frontend URL
            }
            
            # Send bulk invitations
            notification_service.send_bulk_notifications(
                target_employees, "survey_invitation", survey_data
            )
            
        except Exception as e:
            logger.warning(f"Failed to send survey invitations: {e}")
        
        logger.info(f"Survey published: {survey.id} by {current_user.employee_id}")
        
        return {"message": "Survey published and invitations sent"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error publishing survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish survey"
        )

# Survey Response Routes

@router.post("/{survey_id}/responses", response_model=SurveyResponseData)
async def submit_survey_response(
    survey_id: int,
    response_data: SurveyResponseCreate,
    request: Request,
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit survey response
    
    Args:
        survey_id: Survey ID
        response_data: Survey response data
        request: HTTP request object
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        SurveyResponseData: Created survey response
    """
    try:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        # Prepare metadata
        metadata = {
            "ip_address": str(request.client.host),
            "user_agent": request.headers.get("user-agent"),
            "device_type": "desktop",  # This could be enhanced with proper device detection
            "start_time": response_data.start_time.isoformat() if response_data.start_time else None
        }
        
        success, survey_response, errors = survey_service.submit_survey_response(
            db, survey, current_user, response_data.responses, metadata
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Response submission failed: {', '.join(errors)}"
            )
        
        logger.info(f"Survey response submitted: {survey_response.id} for survey {survey_id}")
        
        return SurveyResponseData.from_orm(survey_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting survey response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit survey response"
        )

@router.get("/{survey_id}/responses", response_model=List[SurveyResponseData])
async def get_survey_responses(
    survey_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Get survey responses (HR only)
    
    Args:
        survey_id: Survey ID
        skip: Number of responses to skip
        limit: Maximum number of responses to return
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        List[SurveyResponseData]: List of survey responses
    """
    try:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        # Get responses
        responses = db.query(SurveyResponse).filter(
            SurveyResponse.survey_id == survey_id
        ).order_by(SurveyResponse.created_at.desc())\
         .offset(skip).limit(limit).all()
        
        return [SurveyResponseData.from_orm(response) for response in responses]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving survey responses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve survey responses"
        )

@router.get("/{survey_id}/analytics")
async def get_survey_analytics(
    survey_id: int,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Get survey analytics and insights (HR only)
    
    Args:
        survey_id: Survey ID
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        Dict: Survey analytics data
    """
    try:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Survey not found"
            )
        
        analytics = survey_service.calculate_survey_analytics(db, survey)
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating survey analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics"
        )

# Engagement Metrics Routes

@router.post("/engagement-metrics", response_model=EngagementMetricResponse)
async def create_engagement_metric(
    metric_data: EngagementMetricCreate,
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Create engagement metric (HR only)
    
    Args:
        metric_data: Engagement metric data
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        EngagementMetricResponse: Created engagement metric
    """
    try:
        # Verify employee exists
        employee = db.query(Employee).filter(Employee.id == metric_data.employee_id).first()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        engagement_metric = EngagementMetric(
            employee_id=metric_data.employee_id,
            metric_date=metric_data.metric_date,
            engagement_score=metric_data.engagement_score,
            job_satisfaction_score=metric_data.job_satisfaction_score,
            work_life_balance_score=metric_data.work_life_balance_score,
            career_development_score=metric_data.career_development_score,
            compensation_satisfaction_score=metric_data.compensation_satisfaction_score,
            manager_relationship_score=metric_data.manager_relationship_score,
            team_collaboration_score=metric_data.team_collaboration_score,
            company_culture_score=metric_data.company_culture_score,
            flight_risk_score=metric_data.flight_risk_score,
            burnout_risk_score=metric_data.burnout_risk_score,
            notes=metric_data.notes,
            ai_analyzed=metric_data.ai_analyzed
        )
        
        # Calculate engagement level
        engagement_metric.calculate_engagement_level()
        
        # Set action items
        if metric_data.action_items:
            engagement_metric.set_action_items(metric_data.action_items)
        
        db.add(engagement_metric)
        db.commit()
        db.refresh(engagement_metric)
        
        logger.info(f"Engagement metric created for employee {metric_data.employee_id}")
        
        return EngagementMetricResponse.from_orm(engagement_metric)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating engagement metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create engagement metric"
        )

@router.get("/engagement-metrics", response_model=List[EngagementMetricResponse])
async def get_engagement_metrics(
    employee_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Employee = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get engagement metrics with filtering
    
    Args:
        employee_id: Filter by employee ID
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
        skip: Number of metrics to skip
        limit: Maximum number of metrics to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[EngagementMetricResponse]: List of engagement metrics
    """
    try:
        query = db.query(EngagementMetric)
        
        # Access control
        if current_user.role.title.lower() not in ['hr', 'human resources']:
            # Non-HR users can only see their own metrics
            query = query.filter(EngagementMetric.employee_id == current_user.id)
        elif employee_id:
            query = query.filter(EngagementMetric.employee_id == employee_id)
        
        # Date filters
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(EngagementMetric.metric_date >= date_from_obj)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(EngagementMetric.metric_date <= date_to_obj)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        # Apply pagination and ordering
        metrics = query.order_by(EngagementMetric.metric_date.desc())\
                      .offset(skip).limit(limit).all()
        
        return [EngagementMetricResponse.from_orm(metric) for metric in metrics]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving engagement metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve engagement metrics"
        )

@router.get("/engagement-metrics/dashboard")
async def get_engagement_dashboard(
    current_user: Employee = Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    """
    Get engagement dashboard data (HR only)
    
    Args:
        current_user: Current authenticated user (HR)
        db: Database session
        
    Returns:
        Dict: Engagement dashboard data
    """
    try:
        from sqlalchemy import func
        from datetime import date, timedelta
        
        # Recent metrics (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        
        recent_metrics = db.query(EngagementMetric).filter(
            EngagementMetric.metric_date >= thirty_days_ago
        ).all()
        
        if not recent_metrics:
            return {
                "total_employees_measured": 0,
                "average_engagement_score": 0,
                "engagement_distribution": {},
                "risk_summary": {"high_risk": 0, "medium_risk": 0, "low_risk": 0},
                "trends": "No data available"
            }
        
        # Calculate summary statistics
        total_employees = len(set(metric.employee_id for metric in recent_metrics))
        avg_engagement = sum(float(m.engagement_score) for m in recent_metrics if m.engagement_score) / len(recent_metrics)
        
        # Engagement distribution
        engagement_distribution = {
            "highly_engaged": len([m for m in recent_metrics if m.engagement_score and m.engagement_score >= 80]),
            "engaged": len([m for m in recent_metrics if m.engagement_score and 60 <= m.engagement_score < 80]),
            "moderately_engaged": len([m for m in recent_metrics if m.engagement_score and 40 <= m.engagement_score < 60]),
            "disengaged": len([m for m in recent_metrics if m.engagement_score and m.engagement_score < 40])
        }
        
        # Risk summary
        risk_summary = {
            "high_risk": len([m for m in recent_metrics if m.flight_risk_score and m.flight_risk_score >= 70]),
            "medium_risk": len([m for m in recent_metrics if m.flight_risk_score and 40 <= m.flight_risk_score < 70]),
            "low_risk": len([m for m in recent_metrics if m.flight_risk_score and m.flight_risk_score < 40])
        }
        
        return {
            "total_employees_measured": total_employees,
            "average_engagement_score": round(avg_engagement, 2),
            "engagement_distribution": engagement_distribution,
            "risk_summary": risk_summary,
            "trends": "positive" if avg_engagement >= 70 else "needs_attention",
            "measurement_period": "Last 30 days"
        }
        
    except Exception as e:
        logger.error(f"Error generating engagement dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate engagement dashboard"
        )