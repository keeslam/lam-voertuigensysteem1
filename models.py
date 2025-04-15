from datetime import datetime
import os
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class Vehicle(db.Model):
    """Vehicle model for storing car information"""
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')  # available, rented, maintenance
    daily_rate = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(20))
    mileage = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with rentals
    rentals = db.relationship('Rental', backref='vehicle', lazy=True)
    
    def __repr__(self):
        return f"{self.year} {self.make} {self.model} ({self.license_plate})"


class Customer(db.Model):
    """Customer model for storing customer information"""
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    driver_license = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with rentals
    rentals = db.relationship('Rental', backref='customer', lazy=True)
    
    def __repr__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Rental(db.Model):
    """Rental model for storing rental information"""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    actual_return_date = db.Column(db.Date)
    total_cost = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"Rental #{self.id}: {self.vehicle.license_plate} to {self.customer.full_name}"


class VehicleExpense(db.Model):
    """Model for storing vehicle expenses/costs"""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    expense_type = db.Column(db.String(50), nullable=False)  # maintenance, repair, fuel, etc.
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with vehicle
    vehicle = db.relationship('Vehicle', backref='expenses', lazy=True)
    
    def __repr__(self):
        return f"Expense #{self.id}: {self.expense_type} for {self.vehicle.license_plate} - €{self.amount}"


class VehicleDocument(db.Model):
    """Model for storing vehicle documents (photos, reports, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # damage_photo, apk_report, etc.
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with vehicle
    vehicle = db.relationship('Vehicle', backref='documents', lazy=True)
    
    def __repr__(self):
        return f"Document #{self.id}: {self.document_type} for {self.vehicle.license_plate}"
        
    def get_file_extension(self):
        """Get the file extension from the filename"""
        _, ext = os.path.splitext(self.filename)
        return ext.lower()
    
    def is_image(self):
        """Check if the document is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        return self.get_file_extension() in image_extensions
    
    def is_pdf(self):
        """Check if the document is a PDF"""
        return self.get_file_extension() == '.pdf'


# Define a many-to-many relationship for User and Role
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with roles
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                           backref=db.backref('users', lazy=True))
    
    def __repr__(self):
        return f"User {self.username}"
    
    def set_password(self, password):
        """Set the user password"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if the password is correct"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get the user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name):
        """Check if user has a specific permission through any of their roles"""
        for role in self.roles:
            if any(perm.name == permission_name for perm in role.permissions):
                return True
        return False


class Role(db.Model):
    """Role model for authorization"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    # Relationship with permissions
    permissions = db.relationship('Permission', secondary='role_permissions', lazy='subquery',
                                 backref=db.backref('roles', lazy=True))
    
    def __repr__(self):
        return f"Role {self.name}"


class Permission(db.Model):
    """Permission model for fine-grained access control"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f"Permission {self.name}"


# Define a many-to-many relationship for Role and Permission
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)


# Setup Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load a user by ID for Flask-Login"""
    return User.query.get(int(user_id))
