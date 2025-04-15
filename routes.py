from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, abort, current_app
from sqlalchemy import desc, func
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename

from app import app, db
from models import Vehicle, Customer, Rental, VehicleExpense, VehicleDocument
import document_service
from auth import permission_required

# Add jinja date helpers
@app.template_filter('date')
def _jinja2_filter_date(date, fmt=None):
    if fmt:
        return date.strftime(fmt)
    return date.strftime('%Y-%m-%d')

@app.template_global()
def current_date():
    return date.today()

# Redirect to login
@app.route('/login')
def login_redirect():
    return redirect(url_for('auth.login'))

# Dashboard route
@app.route('/')
@login_required
@permission_required('view_dashboard')
def dashboard():
    # Get counts for the dashboard
    vehicle_count = Vehicle.query.count()
    available_vehicles = Vehicle.query.filter_by(status='available').count()
    customer_count = Customer.query.count()
    active_rentals = Rental.query.filter_by(status='active').count()
    
    # Get recent rentals
    recent_rentals = Rental.query.order_by(desc(Rental.created_at)).limit(5).all()
    
    # Get vehicles due for return today
    today = date.today()
    due_today = Rental.query.filter_by(status='active').filter(Rental.end_date == today).all()
    
    # Get overdue rentals
    overdue = Rental.query.filter_by(status='active').filter(Rental.end_date < today).all()
    
    # Get recent expenses
    recent_expenses = VehicleExpense.query.order_by(desc(VehicleExpense.created_at)).limit(5).all()
    
    # Get total expenses by type
    expenses_by_type = db.session.query(
        VehicleExpense.expense_type, 
        func.sum(VehicleExpense.amount).label('total')
    ).group_by(VehicleExpense.expense_type).all()
    
    return render_template(
        'dashboard.html',
        vehicle_count=vehicle_count,
        available_vehicles=available_vehicles,
        customer_count=customer_count,
        active_rentals=active_rentals,
        recent_rentals=recent_rentals,
        due_today=due_today,
        overdue=overdue,
        recent_expenses=recent_expenses,
        expenses_by_type=expenses_by_type
    )

# Vehicle routes
@app.route('/vehicles')
def vehicles():
    vehicles = Vehicle.query.all()
    return render_template('vehicles.html', vehicles=vehicles)

@app.route('/vehicles/lookup', methods=['GET', 'POST'])
def lookup_vehicle():
    vehicle_data = None
    error_message = None
    
    if request.method == 'POST':
        license_plate = request.form['license_plate']
        
        # Importeer RDW API module
        from rdw_api import RDWApi
        
        # Zoek voertuiginformatie
        vehicle_data = RDWApi.search_by_license_plate(license_plate)
        
        if not vehicle_data:
            error_message = f"Geen voertuiginformatie gevonden voor kenteken {license_plate}. " \
                            f"Controleer of je een geldig Nederlands kenteken hebt ingevoerd."
    
    return render_template('vehicle_lookup.html', 
                          vehicle_data=vehicle_data, 
                          error_message=error_message)

@app.route('/vehicles/add-from-rdw', methods=['POST'])
def add_vehicle_from_rdw():
    try:
        # Maak een nieuw voertuig aan met de gegevens uit het formulier
        new_vehicle = Vehicle(
            make=request.form['make'],
            model=request.form['model'],
            year=int(request.form['year']),
            license_plate=request.form['license_plate'],
            status=request.form['status'],
            daily_rate=float(request.form['daily_rate']),
            color=request.form['color'],
            mileage=int(request.form['mileage'])
        )
        
        # Voeg toe aan database
        db.session.add(new_vehicle)
        db.session.commit()
        
        flash('Voertuig succesvol toegevoegd aan de vloot!', 'success')
        return redirect(url_for('vehicles'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Fout bij toevoegen voertuig: {str(e)}', 'danger')
        return redirect(url_for('lookup_vehicle'))

@app.route('/vehicles/add', methods=['GET', 'POST'])
def add_vehicle():
    if request.method == 'POST':
        # Create a new vehicle
        new_vehicle = Vehicle(
            make=request.form['make'],
            model=request.form['model'],
            year=int(request.form['year']),
            license_plate=request.form['license_plate'],
            status=request.form['status'],
            daily_rate=float(request.form['daily_rate']),
            color=request.form['color'],
            mileage=int(request.form['mileage'])
        )
        
        try:
            db.session.add(new_vehicle)
            db.session.commit()
            flash('Vehicle added successfully!', 'success')
            return redirect(url_for('vehicles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding vehicle: {str(e)}', 'danger')
            
    return render_template('vehicle_form.html', vehicle=None)

@app.route('/vehicles/edit/<int:id>', methods=['GET', 'POST'])
def edit_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update the vehicle
        vehicle.make = request.form['make']
        vehicle.model = request.form['model']
        vehicle.year = int(request.form['year'])
        vehicle.license_plate = request.form['license_plate']
        vehicle.status = request.form['status']
        vehicle.daily_rate = float(request.form['daily_rate'])
        vehicle.color = request.form['color']
        vehicle.mileage = int(request.form['mileage'])
        
        try:
            db.session.commit()
            flash('Vehicle updated successfully!', 'success')
            return redirect(url_for('vehicles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating vehicle: {str(e)}', 'danger')
            
    return render_template('vehicle_form.html', vehicle=vehicle)

@app.route('/vehicles/delete/<int:id>', methods=['POST'])
def delete_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    
    # Check if vehicle is currently rented
    active_rentals = Rental.query.filter_by(vehicle_id=id, status='active').first()
    if active_rentals:
        flash('Cannot delete vehicle that is currently rented', 'danger')
        return redirect(url_for('vehicles'))
    
    try:
        db.session.delete(vehicle)
        db.session.commit()
        flash('Vehicle deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting vehicle: {str(e)}', 'danger')
        
    return redirect(url_for('vehicles'))

# Customer routes
@app.route('/customers')
def customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        # Create a new customer
        new_customer = Customer(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            driver_license=request.form['driver_license']
        )
        
        try:
            db.session.add(new_customer)
            db.session.commit()
            flash('Customer added successfully!', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}', 'danger')
            
    return render_template('customer_form.html', customer=None)

@app.route('/customers/edit/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update the customer
        customer.first_name = request.form['first_name']
        customer.last_name = request.form['last_name']
        customer.email = request.form['email']
        customer.phone = request.form['phone']
        customer.address = request.form['address']
        customer.driver_license = request.form['driver_license']
        
        try:
            db.session.commit()
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
            
    return render_template('customer_form.html', customer=customer)

@app.route('/customers/delete/<int:id>', methods=['POST'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    
    # Check if customer has active rentals
    active_rentals = Rental.query.filter_by(customer_id=id, status='active').first()
    if active_rentals:
        flash('Cannot delete customer with active rentals', 'danger')
        return redirect(url_for('customers'))
    
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'danger')
        
    return redirect(url_for('customers'))

# Rental routes
@app.route('/rentals')
def rentals():
    rentals = Rental.query.all()
    return render_template('rentals.html', rentals=rentals)

@app.route('/rentals/add', methods=['GET', 'POST'])
def add_rental():
    # Get available vehicles
    available_vehicles = Vehicle.query.filter_by(status='available').all()
    customers = Customer.query.all()
    
    if request.method == 'POST':
        vehicle_id = int(request.form['vehicle_id'])
        customer_id = int(request.form['customer_id'])
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        
        # Calculate the total cost
        vehicle = Vehicle.query.get(vehicle_id)
        days = (end_date - start_date).days + 1
        total_cost = days * vehicle.daily_rate
        
        # Create the rental
        new_rental = Rental(
            vehicle_id=vehicle_id,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost,
            status='active',
            notes=request.form.get('notes', '')
        )
        
        try:
            # Update vehicle status
            vehicle.status = 'rented'
            
            db.session.add(new_rental)
            db.session.commit()
            flash('Rental created successfully!', 'success')
            return redirect(url_for('rentals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating rental: {str(e)}', 'danger')
    
    return render_template('rental_form.html', 
                          rental=None, 
                          vehicles=available_vehicles, 
                          customers=customers)

@app.route('/rentals/edit/<int:id>', methods=['GET', 'POST'])
def edit_rental(id):
    rental = Rental.query.get_or_404(id)
    vehicles = Vehicle.query.all()
    customers = Customer.query.all()
    
    if request.method == 'POST':
        # Update the rental
        old_vehicle_id = rental.vehicle_id
        new_vehicle_id = int(request.form['vehicle_id'])
        
        rental.vehicle_id = new_vehicle_id
        rental.customer_id = int(request.form['customer_id'])
        rental.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        rental.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        rental.status = request.form['status']
        rental.notes = request.form.get('notes', '')
        
        # If there's a return date
        if request.form.get('actual_return_date'):
            rental.actual_return_date = datetime.strptime(
                request.form['actual_return_date'], '%Y-%m-%d').date()
        
        # Recalculate total cost
        days = (rental.end_date - rental.start_date).days + 1
        vehicle = Vehicle.query.get(new_vehicle_id)
        rental.total_cost = days * vehicle.daily_rate
        
        try:
            # If vehicle changed or rental completed, update vehicle statuses
            if old_vehicle_id != new_vehicle_id or rental.status == 'completed':
                old_vehicle = Vehicle.query.get(old_vehicle_id)
                old_vehicle.status = 'available'
                
                if rental.status == 'active':
                    vehicle.status = 'rented'
                else:
                    vehicle.status = 'available'
            
            db.session.commit()
            flash('Rental updated successfully!', 'success')
            return redirect(url_for('rentals'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating rental: {str(e)}', 'danger')
    
    return render_template('rental_form.html', 
                          rental=rental, 
                          vehicles=vehicles, 
                          customers=customers)

@app.route('/rentals/return/<int:id>', methods=['POST'])
def return_rental(id):
    rental = Rental.query.get_or_404(id)
    
    if rental.status != 'active':
        flash('This rental is not active and cannot be returned', 'danger')
        return redirect(url_for('rentals'))
    
    # Set the return date to today
    rental.actual_return_date = date.today()
    rental.status = 'completed'
    
    # Mark the vehicle as available
    vehicle = Vehicle.query.get(rental.vehicle_id)
    vehicle.status = 'available'
    
    try:
        db.session.commit()
        flash('Vehicle returned successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error returning vehicle: {str(e)}', 'danger')
        
    return redirect(url_for('rentals'))

# Reports route
@app.route('/reports')
def reports():
    # Vehicles by status
    vehicle_status = db.session.query(
        Vehicle.status, db.func.count(Vehicle.id).label('count')
    ).group_by(Vehicle.status).all()
    
    # Active rentals by customer
    customer_rentals = db.session.query(
        Customer.id,
        Customer.first_name, 
        Customer.last_name,
        db.func.count(Rental.id).label('rental_count')
    ).join(Rental).filter(Rental.status == 'active').group_by(
        Customer.id, Customer.first_name, Customer.last_name
    ).all()
    
    # Revenue by month (last 6 months using SQLite approach for compatibility)
    revenue_by_month = []
    try:
        # Try to fetch the last 6 months of revenue data
        rentals = Rental.query.filter(Rental.status.in_(['active', 'completed'])).all()
        
        # Process the data manually
        revenue_data = {}
        for rental in rentals:
            month_key = f"{rental.start_date.year}-{rental.start_date.month:02d}"
            if month_key not in revenue_data:
                revenue_data[month_key] = 0
            revenue_data[month_key] += rental.total_cost
        
        # Convert to a list of objects similar to SQLAlchemy results
        from collections import namedtuple
        RevenueResult = namedtuple('RevenueResult', ['month', 'revenue'])
        
        # Get the last 6 months or all months if less than 6
        sorted_months = sorted(revenue_data.keys())[-6:]
        for month in sorted_months:
            revenue_by_month.append(RevenueResult(month, revenue_data[month]))
    except Exception as e:
        app.logger.error(f"Error generating revenue report: {str(e)}")
        # Return empty list if there's an error
    
    return render_template('reports.html',
                          vehicle_status=vehicle_status,
                          customer_rentals=customer_rentals,
                          revenue_by_month=revenue_by_month)

# Vehicle Expenses Routes
@app.route('/vehicles/<int:vehicle_id>/expenses')
def vehicle_expenses(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    expenses = VehicleExpense.query.filter_by(vehicle_id=vehicle_id).order_by(desc(VehicleExpense.date)).all()
    return render_template('vehicle_expenses.html', vehicle=vehicle, expenses=expenses)

@app.route('/vehicles/<int:vehicle_id>/expenses/add', methods=['GET', 'POST'])
def add_expense(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    if request.method == 'POST':
        # Create expense from form data
        expense_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        
        new_expense = VehicleExpense(
            vehicle_id=vehicle_id,
            expense_type=request.form['expense_type'],
            amount=float(request.form['amount']),
            date=expense_date,
            description=request.form.get('description', '')
        )
        
        try:
            db.session.add(new_expense)
            db.session.commit()
            flash('Kosten succesvol toegevoegd!', 'success')
            return redirect(url_for('vehicle_expenses', vehicle_id=vehicle_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het toevoegen van kosten: {str(e)}', 'danger')
    
    # Show expense form 
    return render_template('expense_form.html', vehicle=vehicle, expense=None)

@app.route('/vehicles/<int:vehicle_id>/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
def edit_expense(vehicle_id, expense_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    expense = VehicleExpense.query.get_or_404(expense_id)
    
    # Verify expense belongs to vehicle
    if expense.vehicle_id != vehicle_id:
        abort(404)
    
    if request.method == 'POST':
        # Update expense
        expense.expense_type = request.form['expense_type']
        expense.amount = float(request.form['amount'])
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        expense.description = request.form.get('description', '')
        
        try:
            db.session.commit()
            flash('Kosten succesvol bijgewerkt!', 'success')
            return redirect(url_for('vehicle_expenses', vehicle_id=vehicle_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Fout bij het bijwerken van kosten: {str(e)}', 'danger')
    
    return render_template('expense_form.html', vehicle=vehicle, expense=expense)

@app.route('/vehicles/<int:vehicle_id>/expenses/<int:expense_id>/delete', methods=['POST'])
def delete_expense(vehicle_id, expense_id):
    expense = VehicleExpense.query.get_or_404(expense_id)
    
    # Verify expense belongs to vehicle
    if expense.vehicle_id != vehicle_id:
        abort(404)
    
    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Kosten succesvol verwijderd!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fout bij het verwijderen van kosten: {str(e)}', 'danger')
    
    return redirect(url_for('vehicle_expenses', vehicle_id=vehicle_id))

# Vehicle Documents Routes
@app.route('/vehicles/<int:vehicle_id>/documents')
def vehicle_documents(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    documents = document_service.get_vehicle_documents(vehicle_id)
    return render_template('vehicle_documents.html', vehicle=vehicle, documents=documents)

@app.route('/vehicles/<int:vehicle_id>/documents/add', methods=['GET', 'POST'])
def add_document(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    if request.method == 'POST':
        # Check if file was uploaded
        if 'document' not in request.files:
            flash('Geen bestand geselecteerd', 'danger')
            return redirect(request.url)
        
        file = request.files['document']
        
        # Check if file is empty
        if file.filename == '':
            flash('Geen bestand geselecteerd', 'danger')
            return redirect(request.url)
        
        # Save document if valid
        if file and document_service.allowed_file(file.filename):
            document_type = request.form.get('document_type')
            description = request.form.get('description')
            
            document = document_service.save_document(vehicle_id, document_type, file, description)
            
            if document:
                flash('Document succesvol geüpload!', 'success')
                return redirect(url_for('vehicle_documents', vehicle_id=vehicle_id))
            else:
                flash('Fout bij het uploaden van document', 'danger')
        else:
            flash('Niet-toegestaan bestandstype', 'danger')
    
    return render_template('document_form.html', vehicle=vehicle)

@app.route('/documents/download/<int:document_id>')
def download_document(document_id):
    document = document_service.get_document(document_id)
    
    if not document:
        abort(404)
    
    try:
        return send_file(document.filepath, 
                         download_name=document.filename, 
                         as_attachment=True)
    except Exception as e:
        app.logger.error(f"Error downloading file: {str(e)}")
        abort(500)

@app.route('/documents/delete/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    document = document_service.get_document(document_id)
    
    if not document:
        abort(404)
    
    vehicle_id = document.vehicle_id
    
    if document_service.delete_document(document_id):
        flash('Document succesvol verwijderd!', 'success')
    else:
        flash('Fout bij het verwijderen van document', 'danger')
    
    return redirect(url_for('vehicle_documents', vehicle_id=vehicle_id))

@app.route('/documents/share/<int:document_id>', methods=['GET', 'POST'])
def share_document(document_id):
    document = document_service.get_document(document_id)
    
    if not document:
        abort(404)
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('E-mailadres is verplicht', 'danger')
            return redirect(request.url)
        
        # Generate download link
        download_url = request.host_url.rstrip('/') + url_for('download_document', document_id=document.id)
        
        # Prepare email content
        vehicle = document.vehicle
        html_content = f"""
        <h2>Documentdeling van Autoverhuur</h2>
        <p>Er is een document met u gedeeld voor voertuig {vehicle.make} {vehicle.model} ({vehicle.license_plate}).</p>
        <p><strong>Document:</strong> {document.filename}</p>
        <p><strong>Type:</strong> {document.document_type}</p>
        <p><strong>Beschrijving:</strong> {document.description or 'Geen beschrijving'}</p>
        <p>U kunt het document hier downloaden: <a href="{download_url}">Download document</a></p>
        <p>Deze link is publiek toegankelijk en kan met iedereen gedeeld worden.</p>
        """
        
        # Capture the document path for attachment
        document_path = document.filepath
        attachments = [document_path] if os.path.exists(document_path) else []
        
        # We could use the email service here if the user decides to use it in the future
        # For now, just provide the download link
        flash(f'Gebruik deze downloadlink om het document te delen: {download_url}', 'info')
        return redirect(url_for('vehicle_documents', vehicle_id=document.vehicle_id))
    
    return render_template('share_document.html', document=document)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
