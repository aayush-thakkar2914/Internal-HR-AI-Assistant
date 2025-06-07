-- HR AI Assistant Sample Data
-- This script inserts sample data for testing and demonstration purposes

-- Connect as hr_user
CONNECT hr_user/hr_password@//localhost:1521/XE

-- =============================================================================
-- INSERT DEPARTMENTS
-- =============================================================================
INSERT INTO departments (name, description, department_code, budget, location, is_active) VALUES
('Human Resources', 'Manages employee relations, recruitment, and HR policies', 'HR', 500000, 'Mumbai', 1);

INSERT INTO departments (name, description, department_code, budget, location, is_active) VALUES
('Information Technology', 'Manages IT infrastructure, software development, and technical support', 'IT', 1200000, 'Bangalore', 1);

INSERT INTO departments (name, description, department_code, budget, location, is_active) VALUES
('Finance', 'Handles financial planning, accounting, and budget management', 'FIN', 800000, 'Delhi', 1);

INSERT INTO departments (name, description, department_code, budget, location, is_active) VALUES
('Marketing', 'Manages marketing campaigns, brand promotion, and customer engagement', 'MKT', 700000, 'Mumbai', 1);

INSERT INTO departments (name, description, department_code, budget, location, is_active) VALUES
('Operations', 'Oversees daily operations, process improvement, and quality control', 'OPS', 900000, 'Chennai', 1);

INSERT INTO departments (name, description, department_code, budget, location, is_active) VALUES
('Sales', 'Manages sales activities, client relationships, and revenue generation', 'SALES', 600000, 'Pune', 1);

-- =============================================================================
-- INSERT ROLES
-- =============================================================================
-- HR Roles
INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('HR Manager', 'Manages HR operations and team', 'HR_MGR', 4, 1, 80000, 120000, '["HR Management", "Employee Relations", "Policy Development"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('HR Executive', 'Handles recruitment and employee onboarding', 'HR_EXEC', 2, 1, 35000, 55000, '["Recruitment", "Onboarding", "Communication"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('HR Assistant', 'Provides administrative support to HR team', 'HR_ASST', 1, 1, 25000, 40000, '["Administration", "Documentation", "Communication"]', 1);

-- IT Roles
INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('IT Director', 'Leads IT strategy and technology initiatives', 'IT_DIR', 5, 2, 150000, 250000, '["Technology Strategy", "Team Leadership", "Project Management"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Senior Software Engineer', 'Develops and maintains software applications', 'SWE_SR', 3, 2, 70000, 110000, '["Python", "JavaScript", "Database Design", "API Development"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Software Engineer', 'Develops software applications and features', 'SWE', 2, 2, 45000, 75000, '["Programming", "Testing", "Documentation"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('DevOps Engineer', 'Manages deployment and infrastructure automation', 'DEVOPS', 3, 2, 65000, 95000, '["Docker", "Kubernetes", "CI/CD", "Cloud Platforms"]', 1);

-- Finance Roles
INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Finance Manager', 'Manages financial planning and analysis', 'FIN_MGR', 4, 3, 90000, 140000, '["Financial Analysis", "Budgeting", "Compliance"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Accountant', 'Handles accounting and bookkeeping tasks', 'ACCT', 2, 3, 40000, 65000, '["Accounting", "Tally", "Excel", "GST"]', 1);

-- Marketing Roles
INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Marketing Manager', 'Leads marketing campaigns and strategies', 'MKT_MGR', 4, 4, 75000, 115000, '["Digital Marketing", "Campaign Management", "Analytics"]', 1);

INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Digital Marketing Specialist', 'Manages online marketing and social media', 'DM_SPEC', 2, 4, 35000, 60000, '["SEO", "Social Media", "Content Marketing", "Google Ads"]', 1);

-- =============================================================================
-- INSERT EMPLOYEES
-- =============================================================================
-- HR Department Employees
INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number, 
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('HR2024001', 'priya.sharma@company.com', 'priya.sharma', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i', 
        'Priya', 'Sharma', DATE '1985-03-15', 'female', '+919876543210',
        'Rajesh Sharma', '+919876543211', '123 MG Road', 'Mumbai', 'Maharashtra', '400001', 'India',
        1, 1, DATE '2020-01-15', 'active', 'full_time', 100000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('HR2024002', 'amit.kumar@company.com', 'amit.kumar', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Amit', 'Kumar', DATE '1990-07-22', 'male', '+919876543212',
        'Sunita Kumar', '+919876543213', '456 Linking Road', 'Mumbai', 'Maharashtra', '400002', 'India',
        1, 2, 1, DATE '2022-03-01', 'active', 'full_time', 45000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('HR2024003', 'neha.patel@company.com', 'neha.patel', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Neha', 'Patel', DATE '1992-11-08', 'female', '+919876543214',
        'Kiran Patel', '+919876543215', '789 SV Road', 'Mumbai', 'Maharashtra', '400003', 'India',
        1, 3, 1, DATE '2023-06-15', 'active', 'full_time', 32000, 'INR', 'monthly', 1);

-- IT Department Employees
INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('IT2024001', 'rahul.singh@company.com', 'rahul.singh', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Rahul', 'Singh', DATE '1982-05-12', 'male', '+919876543216',
        'Meera Singh', '+919876543217', '101 Brigade Road', 'Bangalore', 'Karnataka', '560001', 'India',
        2, 4, DATE '2018-09-01', 'active', 'full_time', 200000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('IT2024002', 'ananya.iyer@company.com', 'ananya.iyer', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Ananya', 'Iyer', DATE '1988-09-30', 'female', '+919876543218',
        'Suresh Iyer', '+919876543219', '202 Koramangala', 'Bangalore', 'Karnataka', '560002', 'India',
        2, 5, 4, DATE '2021-01-10', 'active', 'full_time', 85000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('IT2024003', 'vikram.joshi@company.com', 'vikram.joshi', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Vikram', 'Joshi', DATE '1991-12-05', 'male', '+919876543220',
        'Kavita Joshi', '+919876543221', '303 Whitefield', 'Bangalore', 'Karnataka', '560003', 'India',
        2, 6, 4, DATE '2022-07-15', 'active', 'full_time', 60000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('IT2024004', 'sara.ahmed@company.com', 'sara.ahmed', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Sara', 'Ahmed', DATE '1989-04-18', 'female', '+919876543222',
        'Farid Ahmed', '+919876543223', '404 Electronic City', 'Bangalore', 'Karnataka', '560004', 'India',
        2, 7, 4, DATE '2021-11-20', 'active', 'full_time', 80000, 'INR', 'monthly', 1);

-- Finance Department Employees
INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('FIN2024001', 'rajesh.gupta@company.com', 'rajesh.gupta', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Rajesh', 'Gupta', DATE '1983-08-25', 'male', '+919876543224',
        'Priya Gupta', '+919876543225', '505 Connaught Place', 'Delhi', 'Delhi', '110001', 'India',
        3, 8, DATE '2019-04-01', 'active', 'full_time', 115000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('FIN2024002', 'kavya.nair@company.com', 'kavya.nair', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Kavya', 'Nair', DATE '1993-02-14', 'female', '+919876543226',
        'Arun Nair', '+919876543227', '606 Karol Bagh', 'Delhi', 'Delhi', '110002', 'India',
        3, 9, 8, DATE '2023-01-15', 'active', 'full_time', 52000, 'INR', 'monthly', 1);

-- Marketing Department Employees
INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('MKT2024001', 'deepika.mehta@company.com', 'deepika.mehta', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Deepika', 'Mehta', DATE '1986-06-20', 'female', '+919876543228',
        'Rohan Mehta', '+919876543229', '707 Bandra West', 'Mumbai', 'Maharashtra', '400050', 'India',
        4, 10, DATE '2020-08-10', 'active', 'full_time', 95000, 'INR', 'monthly', 1);

INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('MKT2024002', 'arjun.reddy@company.com', 'arjun.reddy', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Arjun', 'Reddy', DATE '1994-10-12', 'male', '+919876543230',
        'Lakshmi Reddy', '+919876543231', '808 Powai', 'Mumbai', 'Maharashtra', '400076', 'India',
        4, 11, 10, DATE '2023-05-01', 'active', 'full_time', 48000, 'INR', 'monthly', 1);

-- Update manager references for departments
UPDATE departments SET manager_id = 1 WHERE id = 1; -- HR Manager
UPDATE departments SET manager_id = 4 WHERE id = 2; -- IT Director
UPDATE departments SET manager_id = 8 WHERE id = 3; -- Finance Manager
UPDATE departments SET manager_id = 10 WHERE id = 4; -- Marketing Manager

-- =============================================================================
-- INSERT LEAVE TYPES
-- =============================================================================
INSERT INTO leave_types (name, code, description, max_days_per_year, max_consecutive_days, min_advance_notice_days, 
                        requires_approval, requires_manager_approval, requires_hr_approval, is_paid, is_carry_forward, carry_forward_limit, accrual_rate, is_active)
VALUES ('Annual Leave', 'AL', 'Annual vacation leave for employees', 21, 15, 3, 1, 1, 0, 1, 1, 5, 1.75, 1);

INSERT INTO leave_types (name, code, description, max_days_per_year, max_consecutive_days, min_advance_notice_days,
                        requires_approval, requires_manager_approval, requires_hr_approval, is_paid, is_carry_forward, carry_forward_limit, accrual_rate, is_active)
VALUES ('Sick Leave', 'SL', 'Medical leave for illness or health issues', 12, 7, 0, 1, 1, 0, 1, 0, 0, 1.0, 1);

INSERT INTO leave_types (name, code, description, max_days_per_year, max_consecutive_days, min_advance_notice_days,
                        requires_approval, requires_manager_approval, requires_hr_approval, is_paid, is_carry_forward, carry_forward_limit, accrual_rate, is_active)
VALUES ('Casual Leave', 'CL', 'Short-term leave for personal reasons', 12, 5, 1, 1, 1, 0, 1, 0, 0, 1.0, 1);

INSERT INTO leave_types (name, code, description, max_days_per_year, max_consecutive_days, min_advance_notice_days,
                        requires_approval, requires_manager_approval, requires_hr_approval, is_paid, is_carry_forward, carry_forward_limit, accrual_rate, is_active)
VALUES ('Maternity Leave', 'ML', 'Maternity leave for new mothers', 180, 180, 30, 1, 1, 1, 1, 0, 0, 0, 1);

INSERT INTO leave_types (name, code, description, max_days_per_year, max_consecutive_days, min_advance_notice_days,
                        requires_approval, requires_manager_approval, requires_hr_approval, is_paid, is_carry_forward, carry_forward_limit, accrual_rate, is_active)
VALUES ('Paternity Leave', 'PL', 'Paternity leave for new fathers', 15, 15, 7, 1, 1, 1, 1, 0, 0, 0, 1);

INSERT INTO leave_types (name, code, description, max_days_per_year, max_consecutive_days, min_advance_notice_days,
                        requires_approval, requires_manager_approval, requires_hr_approval, is_paid, is_carry_forward, carry_forward_limit, accrual_rate, is_active)
VALUES ('Emergency Leave', 'EL', 'Emergency leave for urgent situations', 5, 3, 0, 1, 1, 0, 1, 0, 0, 0, 1);

-- =============================================================================
-- INSERT LEAVE BALANCES FOR 2024
-- =============================================================================
-- Annual Leave balances
INSERT INTO leave_balances (employee_id, leave_type_id, year, allocated_days, used_days, pending_days, carry_forward_days)
SELECT e.id, 1, 2024, 21, 0, 0, 0 FROM employees e WHERE e.is_active = 1;

-- Sick Leave balances
INSERT INTO leave_balances (employee_id, leave_type_id, year, allocated_days, used_days, pending_days, carry_forward_days)
SELECT e.id, 2, 2024, 12, 0, 0, 0 FROM employees e WHERE e.is_active = 1;

-- Casual Leave balances
INSERT INTO leave_balances (employee_id, leave_type_id, year, allocated_days, used_days, pending_days, carry_forward_days)
SELECT e.id, 3, 2024, 12, 0, 0, 0 FROM employees e WHERE e.is_active = 1;

-- =============================================================================
-- INSERT SAMPLE LEAVE REQUESTS
-- =============================================================================
INSERT INTO leave_requests (request_id, employee_id, leave_type_id, start_date, end_date, total_days, reason, status, 
                           manager_id, submitted_date, created_by)
VALUES ('LR20240101', 2, 1, DATE '2024-07-15', DATE '2024-07-19', 5, 'Family vacation to Goa', 'approved', 1, 
        TIMESTAMP '2024-06-15 10:30:00', 2);

INSERT INTO leave_requests (request_id, employee_id, leave_type_id, start_date, end_date, total_days, reason, status,
                           manager_id, submitted_date, created_by)
VALUES ('LR20240102', 5, 2, DATE '2024-08-10', DATE '2024-08-12', 3, 'Fever and flu symptoms', 'approved', 4,
        TIMESTAMP '2024-08-09 09:15:00', 5);

INSERT INTO leave_requests (request_id, employee_id, leave_type_id, start_date, end_date, total_days, reason, status,
                           manager_id, submitted_date, created_by)
VALUES ('LR20240103', 6, 3, DATE '2024-09-05', DATE '2024-09-05', 1, 'Personal work - bank visit', 'pending', 4,
        TIMESTAMP '2024-09-03 14:20:00', 6);

-- =============================================================================
-- INSERT SAMPLE DOCUMENTS
-- =============================================================================
INSERT INTO documents (title, description, document_type, file_path, file_name, file_size, file_extension, mime_type,
                      content_text, keywords, access_level, status, author_id, is_searchable, is_active)
VALUES ('Employee Handbook 2024', 'Complete guide for all employees covering policies, procedures, and benefits',
        'handbook', 'documents/employee_handbook_2024.pdf', 'employee_handbook_2024.pdf', 2048576, '.pdf', 'application/pdf',
        'Employee handbook containing company policies, code of conduct, leave policies, benefits information, and general guidelines for all employees.',
        'employee handbook, policies, benefits, guidelines, code of conduct',
        'internal', 'published', 1, 1, 1);

INSERT INTO documents (title, description, document_type, file_path, file_name, file_size, file_extension, mime_type,
                      content_text, keywords, access_level, status, author_id, is_searchable, is_active)
VALUES ('Leave Policy 2024', 'Detailed leave policy covering all types of leave and application procedures',
        'policy', 'documents/leave_policy_2024.pdf', 'leave_policy_2024.pdf', 1024768, '.pdf', 'application/pdf',
        'Leave policy document detailing annual leave, sick leave, maternity leave, paternity leave, emergency leave, and application procedures.',
        'leave policy, annual leave, sick leave, maternity, paternity, emergency leave',
        'internal', 'published', 1, 1, 1);

INSERT INTO documents (title, description, document_type, file_path, file_name, file_size, file_extension, mime_type,
                      content_text, keywords, access_level, status, author_id, is_searchable, is_active)
VALUES ('IT Security Guidelines', 'Information security guidelines and best practices for all employees',
        'policy', 'documents/it_security_guidelines.pdf', 'it_security_guidelines.pdf', 1536000, '.pdf', 'application/pdf',
        'IT security guidelines covering password policies, data protection, email security, and best practices for maintaining information security.',
        'IT security, password policy, data protection, email security, cybersecurity',
        'internal', 'published', 4, 1, 1);

INSERT INTO documents (title, description, document_type, file_path, file_name, file_size, file_extension, mime_type,
                      content_text, keywords, access_level, status, author_id, is_searchable, is_active)
VALUES ('Performance Review Form', 'Annual performance review form template',
        'form', 'documents/performance_review_form.docx', 'performance_review_form.docx', 512000, '.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'Performance review form template for annual employee evaluations including goal setting, achievement assessment, and development planning.',
        'performance review, evaluation, goals, development, appraisal',
        'internal', 'published', 1, 1, 1);

-- =============================================================================
-- INSERT SAMPLE DOCUMENT REQUESTS
-- =============================================================================
INSERT INTO document_requests (request_id, employee_id, document_title, document_type, description, purpose,
                              format_preference, delivery_method, urgency, status, submitted_at)
VALUES ('DR20240101', 5, 'Employment Certificate', 'certification', 'Need employment certificate for visa application',
        'Visa application for overseas travel', 'pdf', 'email', 'high', 'pending', CURRENT_TIMESTAMP);

INSERT INTO document_requests (request_id, employee_id, document_title, document_type, description, purpose,
                              format_preference, delivery_method, urgency, status, submitted_at)
VALUES ('DR20240102', 9, 'Salary Certificate', 'certification', 'Salary certificate required for loan application',
        'Home loan application', 'pdf', 'email', 'normal', 'processing', CURRENT_TIMESTAMP - INTERVAL '2' DAY);

-- =============================================================================
-- INSERT SAMPLE SURVEYS
-- =============================================================================
INSERT INTO surveys (title, description, survey_type, questions, instructions, estimated_duration, is_anonymous,
                    status, start_date, end_date, total_invited, created_by)
VALUES ('Employee Engagement Survey 2024', 'Annual employee engagement and satisfaction survey',
        'engagement', '[{"id":"job_satisfaction","text":"How satisfied are you with your current job?","type":"scale","scale":{"min":1,"max":5,"labels":["Very Dissatisfied","Very Satisfied"]},"required":true},{"id":"work_life_balance","text":"How would you rate your work-life balance?","type":"scale","scale":{"min":1,"max":5,"labels":["Very Poor","Excellent"]},"required":true},{"id":"career_development","text":"Are you satisfied with your career development opportunities?","type":"scale","scale":{"min":1,"max":5,"labels":["Very Dissatisfied","Very Satisfied"]},"required":true},{"id":"manager_relationship","text":"How would you rate your relationship with your manager?","type":"scale","scale":{"min":1,"max":5,"labels":["Very Poor","Excellent"]},"required":true},{"id":"recommendation","text":"Would you recommend this company as a great place to work?","type":"scale","scale":{"min":1,"max":10,"labels":["Not at all likely","Extremely likely"]},"required":true},{"id":"feedback","text":"What suggestions do you have for improving our workplace?","type":"textarea","required":false}]',
        'Please answer all questions honestly. Your responses will help us improve our workplace.',
        15, 1, 'active', CURRENT_TIMESTAMP - INTERVAL '7' DAY, CURRENT_TIMESTAMP + INTERVAL '23' DAY, 11, 1);

-- =============================================================================
-- INSERT SAMPLE SURVEY RESPONSES
-- =============================================================================
INSERT INTO survey_responses (survey_id, employee_id, responses, completion_status, completion_percentage, 
                             started_at, completed_at, duration_seconds)
VALUES (1, 2, '{"job_satisfaction":4,"work_life_balance":3,"career_development":4,"manager_relationship":5,"recommendation":8,"feedback":"Great work environment and supportive team"}',
        'completed', 100, CURRENT_TIMESTAMP - INTERVAL '5' DAY, CURRENT_TIMESTAMP - INTERVAL '5' DAY + INTERVAL '12' MINUTE, 720);

INSERT INTO survey_responses (survey_id, employee_id, responses, completion_status, completion_percentage,
                             started_at, completed_at, duration_seconds)
VALUES (1, 5, '{"job_satisfaction":5,"work_life_balance":4,"career_development":3,"manager_relationship":4,"recommendation":9,"feedback":"Love the challenging projects and learning opportunities"}',
        'completed', 100, CURRENT_TIMESTAMP - INTERVAL '4' DAY, CURRENT_TIMESTAMP - INTERVAL '4' DAY + INTERVAL '8' MINUTE, 480);

INSERT INTO survey_responses (survey_id, employee_id, responses, completion_status, completion_percentage,
                             started_at, completed_at, duration_seconds)
VALUES (1, 6, '{"job_satisfaction":3,"work_life_balance":2,"career_development":3,"manager_relationship":4,"recommendation":6,"feedback":"Work-life balance could be improved"}',
        'completed', 100, CURRENT_TIMESTAMP - INTERVAL '3' DAY, CURRENT_TIMESTAMP - INTERVAL '3' DAY + INTERVAL '10' MINUTE, 600);

-- =============================================================================
-- INSERT SAMPLE ENGAGEMENT METRICS
-- =============================================================================
INSERT INTO engagement_metrics (employee_id, metric_date, engagement_level, engagement_score,
                               job_satisfaction_score, work_life_balance_score, career_development_score,
                               manager_relationship_score, flight_risk_score, survey_based, survey_id)
VALUES (2, DATE '2024-06-01', 'engaged', 78.5, 80, 60, 80, 100, 25, 1, 1);

INSERT INTO engagement_metrics (employee_id, metric_date, engagement_level, engagement_score,
                               job_satisfaction_score, work_life_balance_score, career_development_score,
                               manager_relationship_score, flight_risk_score, survey_based, survey_id)
VALUES (5, DATE '2024-06-01', 'highly_engaged', 85.0, 100, 80, 60, 80, 15, 1, 1);

INSERT INTO engagement_metrics (employee_id, metric_date, engagement_level, engagement_score,
                               job_satisfaction_score, work_life_balance_score, career_development_score,
                               manager_relationship_score, flight_risk_score, survey_based, survey_id)
VALUES (6, DATE '2024-06-01', 'moderately_engaged', 58.0, 60, 40, 60, 80, 45, 1, 1);

-- =============================================================================
-- INSERT SAMPLE CHAT SESSIONS
-- =============================================================================
INSERT INTO chat_sessions (session_id, employee_id, title, category, status, total_messages, user_messages, ai_messages,
                          started_at, ended_at, duration_seconds, satisfaction_rating, was_helpful, resolution_status)
VALUES ('chat_abc123def456', 2, 'Leave Policy Questions', 'leave_management', 'ended', 8, 4, 4,
        CURRENT_TIMESTAMP - INTERVAL '2' DAY, CURRENT_TIMESTAMP - INTERVAL '2' DAY + INTERVAL '15' MINUTE, 900, 5, 1, 'resolved');

INSERT INTO chat_sessions (session_id, employee_id, title, category, status, total_messages, user_messages, ai_messages,
                          started_at, ended_at, duration_seconds, satisfaction_rating, was_helpful, resolution_status)
VALUES ('chat_def456ghi789', 5, 'IT Security Guidelines', 'policy_question', 'ended', 6, 3, 3,
        CURRENT_TIMESTAMP - INTERVAL '1' DAY, CURRENT_TIMESTAMP - INTERVAL '1' DAY + INTERVAL '8' MINUTE, 480, 4, 1, 'resolved');

INSERT INTO chat_sessions (session_id, employee_id, title, category, status, total_messages, user_messages, ai_messages,
                          started_at, last_activity)
VALUES ('chat_ghi789jkl012', 6, 'Benefits Information', 'benefits_inquiry', 'active', 4, 2, 2,
        CURRENT_TIMESTAMP - INTERVAL '30' MINUTE, CURRENT_TIMESTAMP - INTERVAL '5' MINUTE);

-- =============================================================================
-- INSERT SAMPLE QUERY LOGS
-- =============================================================================
INSERT INTO query_logs (chat_session_id, employee_id, user_query, ai_response, query_category, intent_detected,
                       processing_time_ms, tokens_used, model_used, confidence_score, context_retrieved,
                       complexity_level, status, was_helpful, user_rating, user_sentiment)
VALUES (1, 2, 'How many annual leave days am I entitled to?',
        'Based on our leave policy, you are entitled to 21 annual leave days per year. These can be carried forward up to 5 days to the next year if unused.',
        'leave_management', 'leave_entitlement_query', 1250, 45, 'mixtral-8x7b-32768', 0.92, 1,
        'simple', 'answered', 1, 5, 'positive');

INSERT INTO query_logs (chat_session_id, employee_id, user_query, ai_response, query_category, intent_detected,
                       processing_time_ms, tokens_used, model_used, confidence_score, context_retrieved,
                       complexity_level, status, was_helpful, user_rating, user_sentiment)
VALUES (1, 2, 'Can I take 15 consecutive days of annual leave?',
        'Yes, you can take up to 15 consecutive days of annual leave. However, you need to provide at least 3 days advance notice and get manager approval.',
        'leave_management', 'leave_duration_query', 980, 38, 'mixtral-8x7b-32768', 0.89, 1,
        'simple', 'answered', 1, 5, 'neutral');

INSERT INTO query_logs (chat_session_id, employee_id, user_query, ai_response, query_category, intent_detected,
                       processing_time_ms, tokens_used, model_used, confidence_score, context_retrieved,
                       complexity_level, status, was_helpful, user_rating, user_sentiment)
VALUES (2, 5, 'What are the password requirements for company systems?',
        'According to our IT security guidelines, passwords must be at least 8 characters long, contain uppercase and lowercase letters, numbers, and special characters. Passwords should be changed every 90 days.',
        'policy_question', 'password_policy_query', 1100, 52, 'mixtral-8x7b-32768', 0.95, 1,
        'simple', 'answered', 1, 4, 'neutral');

INSERT INTO query_logs (chat_session_id, employee_id, user_query, ai_response, query_category, intent_detected,
                       processing_time_ms, tokens_used, model_used, confidence_score, context_retrieved,
                       complexity_level, status, was_helpful, user_rating, user_sentiment)
VALUES (3, 6, 'What health insurance benefits do we have?',
        'Our company provides comprehensive health insurance coverage including medical, dental, and vision. The company covers 80% of the premium for employees and 60% for dependents. You can find detailed benefit information in the employee handbook.',
        'benefits_inquiry', 'health_insurance_query', 1400, 68, 'mixtral-8x7b-32768', 0.87, 1,
        'medium', 'answered', 1, 4, 'positive');

-- Update some leave balances to reflect usage
UPDATE leave_balances SET used_days = 5 WHERE employee_id = 2 AND leave_type_id = 1 AND year = 2024;
UPDATE leave_balances SET used_days = 3 WHERE employee_id = 5 AND leave_type_id = 2 AND year = 2024;

-- Update leave request approval dates and comments
UPDATE leave_requests SET 
    manager_approval_date = TIMESTAMP '2024-06-16 14:30:00',
    manager_comments = 'Approved. Enjoy your vacation!',
    approved_date = TIMESTAMP '2024-06-16 14:30:00'
WHERE request_id = 'LR20240101';

UPDATE leave_requests SET 
    manager_approval_date = TIMESTAMP '2024-08-09 16:45:00',
    manager_comments = 'Approved. Take care and get well soon.',
    approved_date = TIMESTAMP '2024-08-09 16:45:00'
WHERE request_id = 'LR20240102';

-- =============================================================================
-- CREATE SOME SAMPLE VIEWS AND REPORTS DATA
-- =============================================================================

-- Create additional sample data for reports
INSERT INTO employees (employee_id, email, username, password_hash, first_name, last_name, date_of_birth, gender, phone_number,
                      emergency_contact_name, emergency_contact_phone, address_line1, city, state, postal_code, country,
                      department_id, role_id, manager_id, hire_date, employment_status, employment_type, salary, currency, pay_frequency, is_active)
VALUES ('OPS2024001', 'ravi.krishnan@company.com', 'ravi.krishnan', '$2b$12$LQv3c1yqBwlVhXVFSdYF1OLNwpVSShJGPBaGlzJcEJ7x4kY2.HT/i',
        'Ravi', 'Krishnan', DATE '1987-01-28', 'male', '+919876543232',
        'Sita Krishnan', '+919876543233', '909 T. Nagar', 'Chennai', 'Tamil Nadu', '600017', 'India',
        5, 1, NULL, DATE '2021-05-15', 'active', 'full_time', 85000, 'INR', 'monthly', 1);

-- Add one more role for Operations
INSERT INTO roles (title, description, role_code, level_num, department_id, min_salary, max_salary, required_skills, is_active) VALUES
('Operations Manager', 'Manages daily operations and process improvement', 'OPS_MGR', 4, 5, 75000, 115000, '["Operations Management", "Process Improvement", "Quality Control"]', 1);

-- Update the operations employee to use the correct role
UPDATE employees SET role_id = 12 WHERE employee_id = 'OPS2024001';

-- Update departments manager for operations
UPDATE departments SET manager_id = 12 WHERE id = 5;

-- Add leave balances for the new employee
INSERT INTO leave_balances (employee_id, leave_type_id, year, allocated_days, used_days, pending_days, carry_forward_days)
VALUES (12, 1, 2024, 21, 2, 0, 0);

INSERT INTO leave_balances (employee_id, leave_type_id, year, allocated_days, used_days, pending_days, carry_forward_days)
VALUES (12, 2, 2024, 12, 1, 0, 0);

INSERT INTO leave_balances (employee_id, leave_type_id, year, allocated_days, used_days, pending_days, carry_forward_days)
VALUES (12, 3, 2024, 12, 0, 2, 0);

-- Add some pending leave request
INSERT INTO leave_requests (request_id, employee_id, leave_type_id, start_date, end_date, total_days, reason, status,
                           manager_id, submitted_date, created_by)
VALUES ('LR20240104', 12, 3, DATE '2024-12-23', DATE '2024-12-24', 2, 'Christmas holidays with family', 'pending', NULL,
        CURRENT_TIMESTAMP - INTERVAL '1' HOUR, 12);

-- Update pending days in leave balance
UPDATE leave_balances SET pending_days = 2 WHERE employee_id = 12 AND leave_type_id = 3 AND year = 2024;

-- Add some more document requests
INSERT INTO document_requests (request_id, employee_id, document_title, document_type, description, purpose,
                              format_preference, delivery_method, urgency, status, assigned_to, submitted_at)
VALUES ('DR20240103', 12, 'Experience Letter', 'certification', 'Experience letter for external job application',
        'Job application in another company', 'pdf', 'email', 'normal', 'processing', 1, CURRENT_TIMESTAMP - INTERVAL '3' DAY);

-- =============================================================================
-- INSERT SOME SYSTEM ADMIN DATA
-- =============================================================================

-- Create a system admin user (modify existing HR manager to have admin privileges)
UPDATE employees SET 
    bio = 'HR Manager and System Administrator with 8+ years of experience in human resources and system management.',
    skills = '["HR Management", "Employee Relations", "System Administration", "Policy Development", "Data Analysis"]',
    certifications = '["SHRM-CP", "PHR", "Oracle Certified Professional"]'
WHERE employee_id = 'HR2024001';

-- Add some skills and bio to other employees
UPDATE employees SET 
    bio = 'Experienced software engineer passionate about AI and machine learning applications.',
    skills = '["Python", "Machine Learning", "FastAPI", "React", "PostgreSQL", "Docker"]',
    certifications = '["AWS Solutions Architect", "Python Professional"]'
WHERE employee_id = 'IT2024002';

UPDATE employees SET 
    bio = 'Full-stack developer with expertise in modern web technologies.',
    skills = '["JavaScript", "React", "Node.js", "MongoDB", "GraphQL"]',
    certifications = '["MongoDB Developer", "React Professional"]'
WHERE employee_id = 'IT2024003';

UPDATE employees SET 
    bio = 'DevOps engineer focused on automation and cloud infrastructure.',
    skills = '["Docker", "Kubernetes", "AWS", "Jenkins", "Terraform", "Ansible"]',
    certifications = '["AWS DevOps Professional", "Kubernetes Administrator"]'
WHERE employee_id = 'IT2024004';

-- =============================================================================
-- CREATE SOME ANALYTICS VIEWS
-- =============================================================================

-- Employee count by department
CREATE OR REPLACE VIEW v_employee_count_by_dept AS
SELECT 
    d.name AS department_name,
    d.department_code,
    COUNT(e.id) AS employee_count,
    COUNT(CASE WHEN e.employment_status = 'active' THEN 1 END) AS active_count,
    ROUND(AVG(e.salary), 2) AS avg_salary
FROM departments d
LEFT JOIN employees e ON d.id = e.department_id
GROUP BY d.id, d.name, d.department_code;

-- Leave utilization by employee
CREATE OR REPLACE VIEW v_leave_utilization AS
SELECT 
    e.employee_id,
    e.first_name || ' ' || e.last_name AS employee_name,
    d.name AS department_name,
    lb.year,
    SUM(lb.allocated_days) AS total_allocated,
    SUM(lb.used_days) AS total_used,
    SUM(lb.pending_days) AS total_pending,
    SUM(lb.allocated_days + lb.carry_forward_days - lb.used_days - lb.pending_days) AS total_available,
    ROUND((SUM(lb.used_days) / NULLIF(SUM(lb.allocated_days + lb.carry_forward_days), 0)) * 100, 2) AS utilization_percentage
FROM employees e
JOIN departments d ON e.department_id = d.id
JOIN leave_balances lb ON e.id = lb.employee_id
WHERE e.is_active = 1
GROUP BY e.id, e.employee_id, e.first_name, e.last_name, d.name, lb.year;

-- Document access statistics
CREATE OR REPLACE VIEW v_document_stats AS
SELECT 
    d.id,
    d.title,
    d.document_type,
    d.status,
    d.view_count,
    d.download_count,
    a.first_name || ' ' || a.last_name AS author_name,
    d.created_at,
    CASE 
        WHEN d.view_count > 100 THEN 'High'
        WHEN d.view_count > 50 THEN 'Medium'
        ELSE 'Low'
    END AS popularity
FROM documents d
JOIN employees a ON d.author_id = a.id
WHERE d.is_active = 1;

COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Display summary of inserted data
SELECT 'Data insertion completed successfully!' AS status FROM dual;

SELECT 'Departments: ' || COUNT(*) AS summary FROM departments
UNION ALL
SELECT 'Roles: ' || COUNT(*) FROM roles
UNION ALL
SELECT 'Employees: ' || COUNT(*) FROM employees
UNION ALL
SELECT 'Leave Types: ' || COUNT(*) FROM leave_types
UNION ALL
SELECT 'Leave Balances: ' || COUNT(*) FROM leave_balances
UNION ALL
SELECT 'Leave Requests: ' || COUNT(*) FROM leave_requests
UNION ALL
SELECT 'Documents: ' || COUNT(*) FROM documents
UNION ALL
SELECT 'Document Requests: ' || COUNT(*) FROM document_requests
UNION ALL
SELECT 'Surveys: ' || COUNT(*) FROM surveys
UNION ALL
SELECT 'Survey Responses: ' || COUNT(*) FROM survey_responses
UNION ALL
SELECT 'Engagement Metrics: ' || COUNT(*) FROM engagement_metrics
UNION ALL
SELECT 'Chat Sessions: ' || COUNT(*) FROM chat_sessions
UNION ALL
SELECT 'Query Logs: ' || COUNT(*) FROM query_logs;

-- Test login credentials (all passwords are 'password123')
SELECT 'Test Login Credentials:' AS info FROM dual
UNION ALL
SELECT 'Username: priya.sharma, Password: password123 (HR Manager)' FROM dual
UNION ALL
SELECT 'Username: rahul.singh, Password: password123 (IT Director)' FROM dual
UNION ALL
SELECT 'Username: ananya.iyer, Password: password123 (Senior Engineer)' FROM dual
UNION ALL
SELECT 'Username: amit.kumar, Password: password123 (HR Executive)' FROM dual;"