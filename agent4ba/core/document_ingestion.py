"""Service d'ingestion de documents pour RAG."""

from pathlib import Path
from typing import Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


class DocumentIngestionService:
    """Service de gestion de l'ingestion de documents et création d'index vectoriel."""

    def __init__(self, project_id: str, base_path: str = "agent4ba/data/projects") -> None:
        """
        Initialise le service d'ingestion pour un projet spécifique.

        Args:
            project_id: Identifiant unique du projet
            base_path: Chemin de base pour le stockage des projets
        """
        self.project_id = project_id
        self.base_path = Path(base_path)
        self.project_dir = self.base_path / project_id

        # Définir les répertoires pour ce projet
        self.documents_dir = self.project_dir / "documents"
        self.vectorstore_dir = self.project_dir / "vectorstore"

        # Créer les répertoires s'ils n'existent pas
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)

        # Initialiser le modèle d'embedding
        # Utiliser un modèle léger adapté au Raspberry Pi
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Initialiser le text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            is_separator_regex=False,
        )

    def ingest_document(self, file_path: Path, file_name: str) -> dict[str, Any]:
        """
        Ingère un document PDF dans le système RAG.

        Cette méthode :
        1. Charge et extrait le texte du PDF
        2. Découpe le texte en chunks
        3. Vectorise les chunks avec le modèle d'embedding
        4. Stocke les vecteurs dans l'index FAISS (nouveau ou existant)

        Args:
            file_path: Chemin vers le fichier PDF à ingérer
            file_name: Nom du fichier original

        Returns:
            Dictionnaire contenant les informations sur l'ingestion

        Raises:
            Exception: Si l'ingestion échoue
        """
        try:
            # 1. Charger et extraire le texte du PDF
            loader = PyPDFLoader(str(file_path))
            documents = loader.load()

            # 2. Découper le texte en chunks
            chunks = self.text_splitter.split_documents(documents)

            # Ajouter des métadonnées aux chunks
            for chunk in chunks:
                chunk.metadata["source"] = file_name
                chunk.metadata["project_id"] = self.project_id

            # 3. Vectoriser et stocker dans FAISS
            vectorstore_path = self.vectorstore_dir / "index"

            # Vérifier si un index existe déjà
            if (vectorstore_path.with_suffix(".faiss")).exists():
                # Charger l'index existant
                vectorstore = FAISS.load_local(
                    str(self.vectorstore_dir),
                    self.embeddings,
                    index_name="index",
                    allow_dangerous_deserialization=True,
                )

                # Ajouter les nouveaux chunks
                vectorstore.add_documents(chunks)
            else:
                # Créer un nouvel index
                vectorstore = FAISS.from_documents(chunks, self.embeddings)

            # Sauvegarder l'index sur le disque
            vectorstore.save_local(str(self.vectorstore_dir), index_name="index")

            return {
                "status": "success",
                "file_name": file_name,
                "num_chunks": len(chunks),
                "num_pages": len(documents),
                "vectorstore_path": str(self.vectorstore_dir),
            }

        except Exception as e:
            raise Exception(f"Failed to ingest document {file_name}: {e}") from e

    def get_vectorstore(self) -> FAISS:
        """
        Récupère le vectorstore FAISS pour ce projet.

        Returns:
            Instance du vectorstore FAISS

        Raises:
            FileNotFoundError: Si aucun vectorstore n'existe pour ce projet
        """
        vectorstore_path = self.vectorstore_dir / "index.faiss"

        if not vectorstore_path.exists():
            raise FileNotFoundError(
                f"No vectorstore found for project {self.project_id}. "
                "Please ingest documents first."
            )

        return FAISS.load_local(
            str(self.vectorstore_dir),
            self.embeddings,
            index_name="index",
            allow_dangerous_deserialization=True,
        )
