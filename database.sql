create database collab;

use collab;

create table users (
    user_id int auto_increment primary key,
    full_name varchar(100) not null,
    email varchar(150) unique not null,
    phone varchar(15) unique not null,
    password_hash varchar(255) not null,
    bio text,
    city varchar(100),
    role enum('builder', 'investor') default 'builder',
    is_verified tinyint(1) default 0,
    created_at datetime default current_timestamp
);

create table otp_verifications (
    otp_id int auto_increment primary key,
    email varchar(120) not null,
    otp_code varchar(10) not null,
    is_used tinyint(1) default 0,
    expires_at datetime not null,
    created_at datetime default current_timestamp
);

create table ideas (
    idea_id int auto_increment primary key,
    user_id int not null,
    title varchar(255) not null,
    description text not null,
    category enum('AI/ML','HealthTech','FinTech','CleanTech','EdTech','Other') not null,
    stage enum('Just an idea','Building MVP','Launched','Growing') default 'Just an idea',
    slots_open int default 1,
    is_active tinyint(1) default 1,
    views int default 0,
    created_at datetime default current_timestamp,
    foreign key (user_id) references users(user_id) on delete cascade
);

create table idea_skills (
    skill_id int auto_increment primary key,
    idea_id int not null,
    skill_name varchar(100) not null,
    is_needed tinyint(1) default 1,
    foreign key (idea_id) references ideas(idea_id) on delete cascade
);

create table applications (
    application_id int auto_increment primary key,
    idea_id int not null,
    applicant_id int not null,
    cover_note text,
    skills_offered varchar(255),
    status enum('pending','accepted','rejected') default 'pending',
    applied_at datetime default current_timestamp,
    foreign key (idea_id) references ideas(idea_id) on delete cascade,
    foreign key (applicant_id) references users(user_id) on delete cascade,
    unique key unique_application (idea_id, applicant_id)
);

create table investor_interests (
    interest_id int auto_increment primary key,
    investor_id int not null,
    idea_id int not null,
    note text,
    created_at datetime default current_timestamp,
    foreign key (investor_id) references users(user_id) on delete cascade,
    foreign key (idea_id) references ideas(idea_id) on delete cascade,
    unique key unique_interest (investor_id, idea_id)
);


create table comments (
    comment_id int auto_increment primary key,
    idea_id int not null,
    user_id int not null,
    body text not null,
    created_at datetime default current_timestamp,
    foreign key (idea_id) references ideas(idea_id) on delete cascade,
    foreign key (user_id) references users(user_id) on delete cascade
);
