CREATE DATABASE file_management;
USE file_management;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
CREATE TABLE files (
    id INT AUTO_INCREMENT PRIMARY KEY,       
    filename VARCHAR(300) NOT NULL,          
    filepath VARCHAR(500) NOT NULL,     
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    user_id INT NOT NULL,                   
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

