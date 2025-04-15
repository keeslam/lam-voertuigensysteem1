from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import db
from models import User, Role, Permission

auth_bp = Blueprint('auth', __name__)

# Decorator for checking if a user has a specific role
def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_role(role_name):
                flash(f'Je hebt niet de benodigde rol ({role_name}) om deze actie uit te voeren.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Decorator for checking if a user has a specific permission
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_name):
                flash(f'Je hebt niet de benodigde rechten om deze actie uit te voeren.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Decorator for checking if a user is an admin
def admin_required(f):
    return role_required('admin')(f)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=remember)
                
                # Update last login time
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Dit account is gedeactiveerd. Neem contact op met een beheerder.', 'danger')
        else:
            flash('Ongeldige gebruikersnaam of wachtwoord', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Je bent succesvol uitgelogd.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    roles = Role.query.all()
    return render_template('auth/users.html', users=users, roles=roles)

@auth_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    roles = Role.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        is_active = 'is_active' in request.form
        role_ids = request.form.getlist('roles')
        
        if not username or not email or not password:
            flash('Vul alle verplichte velden in.', 'danger')
            return render_template('auth/user_form.html', roles=roles, user=None)
        
        try:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active
            )
            user.set_password(password)
            
            # Add roles to user
            for role_id in role_ids:
                role = Role.query.get(int(role_id))
                if role:
                    user.roles.append(role)
            
            db.session.add(user)
            db.session.commit()
            flash('Gebruiker succesvol toegevoegd!', 'success')
            return redirect(url_for('auth.users'))
        except IntegrityError:
            db.session.rollback()
            flash('Gebruikersnaam of e-mail is al in gebruik.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het toevoegen van gebruiker: {str(e)}', 'danger')
    
    return render_template('auth/user_form.html', roles=roles, user=None)

@auth_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        is_active = 'is_active' in request.form
        role_ids = request.form.getlist('roles')
        new_password = request.form.get('password')
        
        if not username or not email:
            flash('Vul alle verplichte velden in.', 'danger')
            return render_template('auth/user_form.html', roles=roles, user=user)
        
        try:
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            
            # Update password if provided
            if new_password:
                user.set_password(new_password)
            
            # Update roles
            user.roles = []
            for role_id in role_ids:
                role = Role.query.get(int(role_id))
                if role:
                    user.roles.append(role)
            
            db.session.commit()
            flash('Gebruiker succesvol bijgewerkt!', 'success')
            return redirect(url_for('auth.users'))
        except IntegrityError:
            db.session.rollback()
            flash('Gebruikersnaam of e-mail is al in gebruik.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het bijwerken van gebruiker: {str(e)}', 'danger')
    
    return render_template('auth/user_form.html', roles=roles, user=user)

@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('Je kunt je eigen account niet verwijderen.', 'danger')
        return redirect(url_for('auth.users'))
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Gebruiker succesvol verwijderd!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fout bij het verwijderen van gebruiker: {str(e)}', 'danger')
    
    return redirect(url_for('auth.users'))

@auth_bp.route('/roles')
@login_required
@admin_required
def roles():
    roles = Role.query.all()
    permissions = Permission.query.all()
    return render_template('auth/roles.html', roles=roles, permissions=permissions)

@auth_bp.route('/roles/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_role():
    permissions = Permission.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permission_ids = request.form.getlist('permissions')
        
        if not name:
            flash('Vul alle verplichte velden in.', 'danger')
            return render_template('auth/role_form.html', permissions=permissions, role=None)
        
        try:
            role = Role(name=name, description=description)
            
            # Add permissions to role
            for permission_id in permission_ids:
                permission = Permission.query.get(int(permission_id))
                if permission:
                    role.permissions.append(permission)
            
            db.session.add(role)
            db.session.commit()
            flash('Rol succesvol toegevoegd!', 'success')
            return redirect(url_for('auth.roles'))
        except IntegrityError:
            db.session.rollback()
            flash('Rolnaam is al in gebruik.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het toevoegen van rol: {str(e)}', 'danger')
    
    return render_template('auth/role_form.html', permissions=permissions, role=None)

@auth_bp.route('/roles/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(id):
    role = Role.query.get_or_404(id)
    permissions = Permission.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permission_ids = request.form.getlist('permissions')
        
        if not name:
            flash('Vul alle verplichte velden in.', 'danger')
            return render_template('auth/role_form.html', permissions=permissions, role=role)
        
        try:
            role.name = name
            role.description = description
            
            # Update permissions
            role.permissions = []
            for permission_id in permission_ids:
                permission = Permission.query.get(int(permission_id))
                if permission:
                    role.permissions.append(permission)
            
            db.session.commit()
            flash('Rol succesvol bijgewerkt!', 'success')
            return redirect(url_for('auth.roles'))
        except IntegrityError:
            db.session.rollback()
            flash('Rolnaam is al in gebruik.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het bijwerken van rol: {str(e)}', 'danger')
    
    return render_template('auth/role_form.html', permissions=permissions, role=role)

@auth_bp.route('/roles/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_role(id):
    role = Role.query.get_or_404(id)
    
    # Prevent deletion of admin role
    if role.name == 'admin':
        flash('De admin-rol kan niet worden verwijderd.', 'danger')
        return redirect(url_for('auth.roles'))
    
    try:
        db.session.delete(role)
        db.session.commit()
        flash('Rol succesvol verwijderd!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fout bij het verwijderen van rol: {str(e)}', 'danger')
    
    return redirect(url_for('auth.roles'))

@auth_bp.route('/permissions')
@login_required
@admin_required
def permissions():
    permissions = Permission.query.all()
    return render_template('auth/permissions.html', permissions=permissions)

@auth_bp.route('/permissions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_permission():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Vul alle verplichte velden in.', 'danger')
            return render_template('auth/permission_form.html', permission=None)
        
        try:
            permission = Permission(name=name, description=description)
            db.session.add(permission)
            db.session.commit()
            flash('Permissie succesvol toegevoegd!', 'success')
            return redirect(url_for('auth.permissions'))
        except IntegrityError:
            db.session.rollback()
            flash('Permissienaam is al in gebruik.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het toevoegen van permissie: {str(e)}', 'danger')
    
    return render_template('auth/permission_form.html', permission=None)

@auth_bp.route('/permissions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_permission(id):
    permission = Permission.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Vul alle verplichte velden in.', 'danger')
            return render_template('auth/permission_form.html', permission=permission)
        
        try:
            permission.name = name
            permission.description = description
            db.session.commit()
            flash('Permissie succesvol bijgewerkt!', 'success')
            return redirect(url_for('auth.permissions'))
        except IntegrityError:
            db.session.rollback()
            flash('Permissienaam is al in gebruik.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het bijwerken van permissie: {str(e)}', 'danger')
    
    return render_template('auth/permission_form.html', permission=permission)

@auth_bp.route('/permissions/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_permission(id):
    permission = Permission.query.get_or_404(id)
    
    try:
        db.session.delete(permission)
        db.session.commit()
        flash('Permissie succesvol verwijderd!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fout bij het verwijderen van permissie: {str(e)}', 'danger')
    
    return redirect(url_for('auth.permissions'))

# Initialize default roles and permissions
def init_auth():
    # Create default permissions if they don't exist
    permissions = {
        'view_dashboard': 'Kan het dashboard bekijken',
        'manage_vehicles': 'Kan voertuigen beheren',
        'view_vehicles': 'Kan voertuigen bekijken',
        'manage_customers': 'Kan klanten beheren',
        'view_customers': 'Kan klanten bekijken',
        'manage_rentals': 'Kan verhuringen beheren',
        'view_rentals': 'Kan verhuringen bekijken',
        'manage_expenses': 'Kan kosten beheren',
        'view_expenses': 'Kan kosten bekijken',
        'manage_documents': 'Kan documenten beheren',
        'view_documents': 'Kan documenten bekijken',
        'view_reports': 'Kan rapporten bekijken',
        'manage_users': 'Kan gebruikers beheren',
        'manage_roles': 'Kan rollen beheren',
    }
    
    for name, description in permissions.items():
        if not Permission.query.filter_by(name=name).first():
            permission = Permission(name=name, description=description)
            db.session.add(permission)
    
    # Create default roles if they don't exist
    roles = {
        'admin': 'Beheerder met volledige toegangsrechten',
        'manager': 'Manager met uitgebreide rechten',
        'staff': 'Medewerker met standaard rechten',
        'viewer': 'Gebruiker met alleen leesrechten'
    }
    
    for name, description in roles.items():
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, description=description)
            db.session.add(role)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing roles and permissions: {str(e)}")
        return
    
    # Assign permissions to roles
    admin_role = Role.query.filter_by(name='admin').first()
    manager_role = Role.query.filter_by(name='manager').first()
    staff_role = Role.query.filter_by(name='staff').first()
    viewer_role = Role.query.filter_by(name='viewer').first()
    
    # Reset permissions for each role
    if admin_role:
        admin_role.permissions = Permission.query.all()
    
    if manager_role:
        manager_perms = ['view_dashboard', 'manage_vehicles', 'view_vehicles', 
                         'manage_customers', 'view_customers', 'manage_rentals', 
                         'view_rentals', 'manage_expenses', 'view_expenses',
                         'manage_documents', 'view_documents', 'view_reports']
        manager_role.permissions = Permission.query.filter(Permission.name.in_(manager_perms)).all()
    
    if staff_role:
        staff_perms = ['view_dashboard', 'view_vehicles', 'view_customers', 
                       'manage_rentals', 'view_rentals', 'view_expenses', 
                       'view_documents']
        staff_role.permissions = Permission.query.filter(Permission.name.in_(staff_perms)).all()
    
    if viewer_role:
        viewer_perms = ['view_dashboard', 'view_vehicles', 'view_customers', 
                        'view_rentals', 'view_expenses', 'view_documents']
        viewer_role.permissions = Permission.query.filter(Permission.name.in_(viewer_perms)).all()
    
    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@autoverhuur.nl',
            first_name='Admin',
            last_name='Gebruiker',
            is_active=True
        )
        admin_user.set_password('admin123')  # This is a default password, should be changed
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error assigning permissions to roles: {str(e)}")