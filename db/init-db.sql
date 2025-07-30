-- PostgreSQL 다중 데이터베이스 초기화 스크립트

-- 데이터베이스 생성
CREATE DATABASE auth_db;
CREATE DATABASE account_db;
CREATE DATABASE user_db;
CREATE DATABASE hospital_db;
CREATE DATABASE review_db;
CREATE DATABASE reservation_db;
CREATE DATABASE doctor_db;
CREATE DATABASE package_db;

-- 권한은 기본 사용자(POSTGRES_USER)가 자동으로 소유함

-- 확인 메시지
\echo 'Multi-database setup completed successfully!'