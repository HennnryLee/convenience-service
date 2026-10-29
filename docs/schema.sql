-- 便民服务平台 数据库脚本
-- 由 scripts/generate_schema.py 自动生成（SQLite 语法）
-- 目标数据库：SQLite；切换 MySQL 时把 INTEGER PRIMARY KEY 改为 INT AUTO_INCREMENT PRIMARY KEY

CREATE TABLE services (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	description TEXT, 
	address VARCHAR(200), 
	price NUMERIC(10, 2) NOT NULL, 
	duration_minutes INTEGER NOT NULL, 
	daily_capacity INTEGER NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_service_status CHECK (status IN ('online', 'offline')), 
	CONSTRAINT ck_service_capacity CHECK (daily_capacity > 0), 
	CONSTRAINT ck_service_price CHECK (price >= 0)
);

CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(20) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	phone VARCHAR(11), 
	real_name VARCHAR(30), 
	role VARCHAR(10) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_user_role CHECK (role IN ('user', 'admin')), 
	CONSTRAINT ck_username_len CHECK (length(username) >= 3), 
	UNIQUE (email)
);

CREATE TABLE announcements (
	id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	content TEXT NOT NULL, 
	author_id INTEGER, 
	is_published BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(author_id) REFERENCES users (id)
);

CREATE TABLE appointments (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	service_id INTEGER NOT NULL, 
	appointment_date DATE NOT NULL, 
	time_slot VARCHAR(20) NOT NULL, 
	contact_name VARCHAR(30) NOT NULL, 
	contact_phone VARCHAR(11) NOT NULL, 
	remark TEXT, 
	status VARCHAR(10) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_appt_status CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(service_id) REFERENCES services (id)
);

CREATE TABLE feedbacks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	service_id INTEGER NOT NULL, 
	appointment_id INTEGER, 
	rating INTEGER NOT NULL, 
	content TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_feedback_rating CHECK (rating BETWEEN 1 AND 5), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	UNIQUE (appointment_id), 
	FOREIGN KEY(appointment_id) REFERENCES appointments (id)
);
