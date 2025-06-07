"""
Survey and engagement management service for the HR AI Assistant.

This service handles survey creation, response collection, and engagement analytics.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.survey import Survey, SurveyResponse, EngagementMetric, SurveyStatus, EngagementLevel
from app.models.employee import Employee
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SurveyService:
    """Survey and engagement management service"""
    
    def __init__(self):
        # Default survey templates
        self.survey_templates = {
            "engagement": {
                "title": "Employee Engagement Survey",
                "description": "Help us understand your engagement and satisfaction at work",
                "questions": [
                    {
                        "id": "job_satisfaction",
                        "text": "How satisfied are you with your current job?",
                        "type": "scale",
                        "scale": {"min": 1, "max": 5, "labels": ["Very Dissatisfied", "Very Satisfied"]},
                        "required": True
                    },
                    {
                        "id": "work_life_balance",
                        "text": "How would you rate your work-life balance?",
                        "type": "scale",
                        "scale": {"min": 1, "max": 5, "labels": ["Very Poor", "Excellent"]},
                        "required": True
                    },
                    {
                        "id": "career_development",
                        "text": "Are you satisfied with your career development opportunities?",
                        "type": "scale",
                        "scale": {"min": 1, "max": 5, "labels": ["Very Dissatisfied", "Very Satisfied"]},
                        "required": True
                    },
                    {
                        "id": "manager_relationship",
                        "text": "How would you rate your relationship with your manager?",
                        "type": "scale",
                        "scale": {"min": 1, "max": 5, "labels": ["Very Poor", "Excellent"]},
                        "required": True
                    },
                    {
                        "id": "recommendation",
                        "text": "Would you recommend this company as a great place to work?",
                        "type": "scale",
                        "scale": {"min": 1, "max": 10, "labels": ["Not at all likely", "Extremely likely"]},
                        "required": True
                    },
                    {
                        "id": "feedback",
                        "text": "What suggestions do you have for improving our workplace?",
                        "type": "textarea",
                        "required": False
                    }
                ]
            }
        }
    
    def create_survey_from_template(self, db: Session, creator: Employee,
                                  template_name: str, customizations: Dict[str, Any] = None) -> Tuple[bool, Optional[Survey], List[str]]:
        """
        Create survey from predefined template
        
        Args:
            db: Database session
            creator: User creating the survey
            template_name: Name of template to use
            customizations: Custom modifications to template
            
        Returns:
            Tuple[bool, Optional[Survey], List[str]]: (success, survey, errors)
        """
        try:
            if template_name not in self.survey_templates:
                return False, None, [f"Template '{template_name}' not found"]
            
            template = self.survey_templates[template_name].copy()
            
            # Apply customizations
            if customizations:
                template.update(customizations)
            
            survey = Survey(
                title=template["title"],
                description=template["description"],
                survey_type=template_name,
                questions=json.dumps(template["questions"]),
                created_by=creator.id,
                status=SurveyStatus.DRAFT
            )
            
            db.add(survey)
            db.commit()
            db.refresh(survey)
            
            logger.info(f"Survey created from template: {survey.id}")
            return True, survey, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating survey from template: {e}")
            return False, None, [f"Error creating survey: {str(e)}"]
    
    def submit_survey_response(self, db: Session, survey: Survey, employee: Employee,
                             responses: Dict[str, Any], metadata: Dict[str, Any] = None) -> Tuple[bool, Optional[SurveyResponse], List[str]]:
        """
        Submit survey response
        
        Args:
            db: Database session
            survey: Survey being responded to
            employee: Employee submitting response
            responses: Survey responses
            metadata: Additional metadata (device, IP, etc.)
            
        Returns:
            Tuple[bool, Optional[SurveyResponse], List[str]]: (success, response, errors)
        """
        try:
            # Check if survey is active
            if not survey.is_active:
                return False, None, ["Survey is not currently active"]
            
            # Check if employee already responded (if not allowing multiple responses)
            if not survey.allow_multiple_responses:
                existing_response = db.query(SurveyResponse).filter(
                    and_(
                        SurveyResponse.survey_id == survey.id,
                        SurveyResponse.employee_id == employee.id,
                        SurveyResponse.completion_status == "completed"
                    )
                ).first()
                
                if existing_response:
                    return False, None, ["You have already completed this survey"]
            
            # Calculate completion percentage
            total_questions = len(survey.get_questions())
            answered_questions = len([v for v in responses.values() if v is not None and v != ""])
            completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Create response record
            survey_response = SurveyResponse(
                survey_id=survey.id,
                employee_id=employee.id if not survey.is_anonymous else None,
                responses=json.dumps(responses),
                completion_status="completed" if completion_percentage >= 80 else "in_progress",
                completion_percentage=completion_percentage,
                completed_at=datetime.utcnow() if completion_percentage >= 80 else None,
                ip_address=metadata.get("ip_address") if metadata else None,
                user_agent=metadata.get("user_agent") if metadata else None,
                device_type=metadata.get("device_type") if metadata else None
            )
            
            # Calculate duration if start time provided
            if metadata and metadata.get("start_time"):
                try:
                    start_time = datetime.fromisoformat(metadata["start_time"])
                    survey_response.duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
                except:
                    pass
            
            db.add(survey_response)
            
            # Update survey statistics
            survey.total_responses += 1
            if completion_percentage >= 80:
                survey.completion_rate = ((survey.completion_rate * (survey.total_responses - 1)) + 100) / survey.total_responses
            
            db.commit()
            db.refresh(survey_response)
            
            # Generate engagement metrics if this is an engagement survey
            if survey.survey_type == "engagement" and completion_percentage >= 80:
                self._generate_engagement_metrics(db, employee, survey_response, responses)
            
            logger.info(f"Survey response submitted: {survey_response.id}")
            return True, survey_response, []
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error submitting survey response: {e}")
            return False, None, [f"Error submitting response: {str(e)}"]
    
    def _generate_engagement_metrics(self, db: Session, employee: Employee, 
                                   survey_response: SurveyResponse, responses: Dict[str, Any]):
        """Generate engagement metrics from survey responses"""
        try:
            # Calculate individual scores (assuming 1-5 scale for most questions)
            job_satisfaction = self._normalize_score(responses.get("job_satisfaction"), 5)
            work_life_balance = self._normalize_score(responses.get("work_life_balance"), 5)
            career_development = self._normalize_score(responses.get("career_development"), 5)
            manager_relationship = self._normalize_score(responses.get("manager_relationship"), 5)
            
            # NPS score (0-10 scale)
            nps_score = responses.get("recommendation", 0)
            
            # Calculate overall engagement score
            engagement_score = (
                job_satisfaction * 0.25 +
                work_life_balance * 0.20 +
                career_development * 0.20 +
                manager_relationship * 0.15 +
                (nps_score / 10 * 100) * 0.20
            )
            
            # Calculate risk scores (basic heuristics)
            flight_risk = 100 - engagement_score
            if nps_score <= 6:  # Detractors
                flight_risk += 20
            elif nps_score >= 9:  # Promoters
                flight_risk -= 20
            
            flight_risk = max(0, min(100, flight_risk))
            
            # Create engagement metric record
            engagement_metric = EngagementMetric(
                employee_id=employee.id,
                metric_date=datetime.utcnow().date(),
                engagement_score=engagement_score,
                job_satisfaction_score=job_satisfaction,
                work_life_balance_score=work_life_balance,
                career_development_score=career_development,
                manager_relationship_score=manager_relationship,
                flight_risk_score=flight_risk,
                survey_based=True,
                survey_id=survey_response.survey_id
            )
            
            # Set engagement level based on score
            engagement_metric.calculate_engagement_level()
            
            db.add(engagement_metric)
            db.commit()
            
            logger.info(f"Engagement metrics generated for employee {employee.id}")
            
        except Exception as e:
            logger.error(f"Error generating engagement metrics: {e}")
    
    def _normalize_score(self, score: Any, max_scale: int) -> float:
        """Normalize score to 0-100 scale"""
        try:
            if score is None:
                return 50.0  # Default neutral score
            
            numeric_score = float(score)
            return (numeric_score / max_scale) * 100
        except (ValueError, TypeError):
            return 50.0
    
    def calculate_survey_analytics(self, db: Session, survey: Survey) -> Dict[str, Any]:
        """
        Calculate comprehensive analytics for a survey
        
        Args:
            db: Database session
            survey: Survey to analyze
            
        Returns:
            Dict: Analytics data
        """
        try:
            # Basic statistics
            total_responses = db.query(SurveyResponse).filter(
                SurveyResponse.survey_id == survey.id
            ).count()
            
            completed_responses = db.query(SurveyResponse).filter(
                and_(
                    SurveyResponse.survey_id == survey.id,
                    SurveyResponse.completion_status == "completed"
                )
            ).count()
            
            # Response rate
            response_rate = (total_responses / survey.total_invited * 100) if survey.total_invited > 0 else 0
            completion_rate = (completed_responses / total_responses * 100) if total_responses > 0 else 0
            
            # Average duration
            avg_duration = db.query(func.avg(SurveyResponse.duration_seconds)).filter(
                and_(
                    SurveyResponse.survey_id == survey.id,
                    SurveyResponse.duration_seconds.isnot(None)
                )
            ).scalar() or 0
            
            # Question-wise analytics
            question_analytics = {}
            if completed_responses > 0:
                responses = db.query(SurveyResponse).filter(
                    and_(
                        SurveyResponse.survey_id == survey.id,
                        SurveyResponse.completion_status == "completed"
                    )
                ).all()
                
                question_analytics = self._analyze_question_responses(survey.get_questions(), responses)
            
            return {
                "total_responses": total_responses,
                "completed_responses": completed_responses,
                "response_rate": response_rate,
                "completion_rate": completion_rate,
                "average_duration_minutes": avg_duration / 60 if avg_duration else 0,
                "question_analytics": question_analytics,
                "demographic_breakdown": self._get_demographic_breakdown(db, survey.id),
                "engagement_insights": self._get_engagement_insights(db, survey.id) if survey.survey_type == "engagement" else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating survey analytics: {e}")
            return {"error": str(e)}
    
    def _analyze_question_responses(self, questions: List[Dict], responses: List[SurveyResponse]) -> Dict[str, Any]:
        """Analyze responses for each question"""
        analytics = {}
        
        for question in questions:
            question_id = question["id"]
            question_type = question["type"]
            
            # Collect all responses for this question
            question_responses = []
            for response in responses:
                response_data = response.get_responses()
                if question_id in response_data and response_data[question_id] is not None:
                    question_responses.append(response_data[question_id])
            
            if not question_responses:
                continue
            
            # Analyze based on question type
            if question_type in ["scale", "rating"]:
                analytics[question_id] = {
                    "type": question_type,
                    "response_count": len(question_responses),
                    "average": sum(question_responses) / len(question_responses),
                    "min": min(question_responses),
                    "max": max(question_responses),
                    "distribution": self._get_distribution(question_responses)
                }
            elif question_type in ["single_choice", "multiple_choice"]:
                analytics[question_id] = {
                    "type": question_type,
                    "response_count": len(question_responses),
                    "choices": self._get_choice_distribution(question_responses)
                }
            elif question_type in ["text", "textarea"]:
                analytics[question_id] = {
                    "type": question_type,
                    "response_count": len(question_responses),
                    "average_length": sum(len(str(r)) for r in question_responses) / len(question_responses),
                    "keyword_analysis": self._analyze_text_responses(question_responses)
                }
        
        return analytics
    
    def _get_distribution(self, values: List[float]) -> Dict[str, int]:
        """Get distribution of numeric values"""
        distribution = {}
        for value in values:
            key = str(int(value))
            distribution[key] = distribution.get(key, 0) + 1
        return distribution
    
    def _get_choice_distribution(self, choices: List[str]) -> Dict[str, int]:
        """Get distribution of choice responses"""
        distribution = {}
        for choice in choices:
            distribution[choice] = distribution.get(choice, 0) + 1
        return distribution
    
    def _analyze_text_responses(self, texts: List[str]) -> Dict[str, int]:
        """Basic keyword analysis of text responses"""
        keywords = {}
        common_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "a", "an", "is", "are", "was", "were"}
        
        for text in texts:
            words = str(text).lower().split()
            for word in words:
                word = word.strip(".,!?;:")
                if len(word) > 3 and word not in common_words:
                    keywords[word] = keywords.get(word, 0) + 1
        
        # Return top 10 keywords
        return dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def _get_demographic_breakdown(self, db: Session, survey_id: int) -> Dict[str, Any]:
        """Get demographic breakdown of survey responses"""
        # This would need to be implemented based on your specific demographic data needs
        return {}
    
    def _get_engagement_insights(self, db: Session, survey_id: int) -> Dict[str, Any]:
        """Get engagement-specific insights"""
        try:
            # Get recent engagement metrics related to this survey
            metrics = db.query(EngagementMetric).filter(
                EngagementMetric.survey_id == survey_id
            ).all()
            
            if not metrics:
                return {}
            
            total_metrics = len(metrics)
            avg_engagement = sum(float(m.engagement_score) for m in metrics if m.engagement_score) / total_metrics
            
            # Calculate risk distribution
            risk_distribution = {
                "low_risk": len([m for m in metrics if m.flight_risk_score and m.flight_risk_score < 30]),
                "medium_risk": len([m for m in metrics if m.flight_risk_score and 30 <= m.flight_risk_score < 60]),
                "high_risk": len([m for m in metrics if m.flight_risk_score and m.flight_risk_score >= 60])
            }
            
            return {
                "average_engagement_score": avg_engagement,
                "total_metrics": total_metrics,
                "risk_distribution": risk_distribution,
                "engagement_trends": "positive" if avg_engagement >= 70 else "needs_attention"
            }
            
        except Exception as e:
            logger.error(f"Error getting engagement insights: {e}")
            return {}

# Global survey service instance
survey_service = SurveyService()