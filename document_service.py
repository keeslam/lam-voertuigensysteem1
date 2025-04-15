import os
import shutil
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from models import VehicleDocument, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'documents')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_document(vehicle_id, document_type, file, description=None):
    """
    Save a document file and create a database record
    
    Args:
        vehicle_id (int): ID of the vehicle
        document_type (str): Type of document
        file (FileStorage): File object from Flask request
        description (str): Optional description
        
    Returns:
        VehicleDocument: The saved document object or None if error
    """
    try:
        if file and allowed_file(file.filename):
            # Secure the filename
            original_filename = secure_filename(file.filename)
            
            # Create a unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{original_filename}"
            
            # Ensure upload directory exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Full path for the file
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save the file
            file.save(filepath)
            
            # Create database record
            document = VehicleDocument(
                vehicle_id=vehicle_id,
                document_type=document_type,
                filename=original_filename,
                filepath=filepath,
                description=description
            )
            
            db.session.add(document)
            db.session.commit()
            
            logger.info(f"Document saved: {filepath}")
            return document
        
        return None
    
    except Exception as e:
        logger.error(f"Error saving document: {str(e)}")
        if 'document' in locals():
            db.session.rollback()
        return None

def get_vehicle_documents(vehicle_id):
    """Get all documents for a vehicle"""
    return VehicleDocument.query.filter_by(vehicle_id=vehicle_id).all()

def get_document(document_id):
    """Get a document by ID"""
    return VehicleDocument.query.get(document_id)

def delete_document(document_id):
    """Delete a document and its file"""
    try:
        document = get_document(document_id)
        if document:
            # Delete the file
            if os.path.exists(document.filepath):
                os.remove(document.filepath)
            
            # Delete the database record
            db.session.delete(document)
            db.session.commit()
            
            logger.info(f"Document deleted: {document.filepath}")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        db.session.rollback()
        return False

def generate_download_link(document_id, base_url):
    """Generate a download link for a document"""
    return f"{base_url}/documents/download/{document_id}"