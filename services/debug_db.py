
from services.database import get_db_service
from models.paper import Paper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_db")

def test_persistence():
    db = get_db_service()
    logger.info(f"DB URL in use: {db.database_url}")
    
    initial_count = db.count_papers()
    logger.info(f"Initial count: {initial_count}")
    
    logger.info("Creating dummy paper...")
    try:
        paper = db.create_paper(
            hash="DEBUG_HASH_123",
            doi="10.123/debug",
            titulo="Debug Paper Persistence",
            archivo_path="/tmp/debug.pdf",
            archivo_nombre="debug.pdf"
        )
        logger.info(f"Created paper ID: {paper.id}")
    except Exception as e:
        logger.error(f"Error creating paper: {e}")
        return

    # Verify immediately
    p2 = db.get_paper_by_id(str(paper.id))
    if p2:
        logger.info("Paper found immediately via get_paper_by_id.")
    else:
        logger.error("Paper NOT found immediately!")

    final_count = db.count_papers()
    logger.info(f"Final count: {final_count}")
    
    if final_count > initial_count:
        logger.info("PERSISTENCE SUCCESSFUL (in this session).")
    else:
        logger.error("PERSISTENCE FAILED.")

if __name__ == "__main__":
    test_persistence()
