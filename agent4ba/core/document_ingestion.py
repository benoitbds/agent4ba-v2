"""Service d'ingestion de documents pour RAG."""

import re
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

    def delete_document(self, document_name: str) -> dict[str, Any]:
        """
        Supprime un document et ses vecteurs associés de l'index FAISS.

        Cette méthode :
        1. Valide le nom du document pour éviter les attaques path traversal
        2. Supprime le fichier physique du disque
        3. Charge l'index FAISS existant
        4. Identifie et supprime les vecteurs associés au document
        5. Sauvegarde l'index FAISS mis à jour

        Args:
            document_name: Nom du fichier à supprimer

        Returns:
            Dictionnaire contenant les informations sur la suppression

        Raises:
            ValueError: Si le nom du document contient des caractères dangereux
            FileNotFoundError: Si le document n'existe pas
            Exception: Si la suppression échoue
        """
        # Validation de sécurité : empêcher les attaques de type path traversal
        if not re.match(r'^[a-zA-Z0-9._-]+$', document_name):
            raise ValueError(
                f"Invalid document_name '{document_name}': "
                "only alphanumeric characters, dots, hyphens and underscores are allowed"
            )

        # Vérifier qu'il n'y a pas de séquences dangereuses
        if '..' in document_name or document_name.startswith('/') or document_name.startswith('\\'):
            raise ValueError(
                f"Invalid document_name '{document_name}': "
                "path traversal attempts are not allowed"
            )

        # Vérifier que le fichier existe
        document_path = self.documents_dir / document_name
        if not document_path.exists():
            raise FileNotFoundError(
                f"Document '{document_name}' not found in project {self.project_id}"
            )

        # Vérifier que c'est bien un fichier (pas un répertoire)
        if not document_path.is_file():
            raise ValueError(
                f"'{document_name}' is not a file"
            )

        try:
            # Vérifier si un vectorstore existe
            vectorstore_path = self.vectorstore_dir / "index.faiss"
            vectors_deleted = 0

            if vectorstore_path.exists():
                # Charger le vectorstore existant
                vectorstore = FAISS.load_local(
                    str(self.vectorstore_dir),
                    self.embeddings,
                    index_name="index",
                    allow_dangerous_deserialization=True,
                )

                # Récupérer tous les documents avec leurs métadonnées
                # FAISS dans LangChain stocke les documents dans docstore
                docstore = vectorstore.docstore
                index_to_docstore_id = vectorstore.index_to_docstore_id

                # Identifier les IDs des documents à supprimer
                ids_to_delete = []
                for _idx, doc_id in index_to_docstore_id.items():
                    doc = docstore.search(doc_id)
                    if doc and doc.metadata.get("source") == document_name:
                        ids_to_delete.append(doc_id)

                # Supprimer les vecteurs associés
                if ids_to_delete:
                    # LangChain FAISS a une méthode delete() qui prend une liste d'IDs
                    vectorstore.delete(ids_to_delete)
                    vectors_deleted = len(ids_to_delete)

                    # Sauvegarder l'index mis à jour
                    vectorstore.save_local(str(self.vectorstore_dir), index_name="index")

            # Supprimer le fichier physique
            document_path.unlink()

            return {
                "status": "success",
                "document_name": document_name,
                "vectors_deleted": vectors_deleted,
                "message": (
                    f"Document '{document_name}' and {vectors_deleted} "
                    "associated vectors deleted successfully"
                ),
            }

        except Exception as e:
            raise Exception(f"Failed to delete document {document_name}: {e}") from e
