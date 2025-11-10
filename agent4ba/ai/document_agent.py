"""Document agent for extracting requirements from unstructured text."""

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from litellm import completion

from agent4ba.core.document_ingestion import DocumentIngestionService
from agent4ba.core.models import WorkItem
from agent4ba.core.storage import ProjectContextService

# Charger les variables d'environnement
load_dotenv()


def load_extract_requirements_prompt() -> dict[str, Any]:
    """
    Charge le prompt d'extraction d'exigences depuis le fichier YAML.

    Returns:
        Dictionnaire contenant le prompt et les exemples
    """
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "extract_requirements.yaml"
    with prompt_path.open("r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
        if not isinstance(result, dict):
            raise ValueError("Invalid prompt configuration")
        return result


def extract_requirements(state: Any) -> dict[str, Any]:
    """
    Extrait les exigences en utilisant RAG (Retrieval-Augmented Generation).

    Cette fonction :
    1. Charge la Vector Store FAISS du projet
    2. Utilise la requête utilisateur pour rechercher les documents pertinents
    3. Injecte ces documents comme contexte dans le prompt au LLM

    Args:
        state: État actuel du graphe contenant project_id et user_query

    Returns:
        Mise à jour de l'état avec impact_plan et status
    """
    print("[DOCUMENT_AGENT] Extracting requirements using RAG...")

    # Récupérer le project_id et la requête utilisateur
    project_id = state.get("project_id", "")
    user_query = state.get("user_query", "")

    if not user_query or not user_query.strip():
        print("[DOCUMENT_AGENT] No user query provided")
        return {
            "status": "error",
            "result": "No user query provided for requirement extraction",
        }

    print(f"[DOCUMENT_AGENT] User query: {user_query}")

    # Initialiser la liste d'événements
    agent_events = []

    # Émettre l'événement AgentStart avec la reformulation
    agent_events.append({
        "type": "agent_start",
        "thought": f"Compris ! Je vais extraire les exigences pertinentes des documents en me basant sur votre recherche : « {user_query} ».",
        "agent_name": "DocumentAgent",
    })

    # Émettre le plan d'action
    agent_events.append({
        "type": "agent_plan",
        "steps": [
            "Chargement de la Vector Store du projet",
            "Recherche des documents pertinents (RAG)",
            "Extraction des exigences via LLM",
            "Validation et construction de l'ImpactPlan",
        ],
        "agent_name": "DocumentAgent",
    })

    # Initialiser le service d'ingestion pour accéder au vectorstore
    agent_events.append({
        "type": "tool_used",
        "tool_name": "Chargement Vector Store",
        "tool_icon": "🗄️",
        "description": "Chargement de la base vectorielle des documents",
        "status": "running",
    })

    try:
        ingestion_service = DocumentIngestionService(project_id)
        vectorstore = ingestion_service.get_vectorstore()
        print("[DOCUMENT_AGENT] Vector store loaded successfully")
        agent_events[-1]["status"] = "completed"
    except FileNotFoundError as e:
        print(f"[DOCUMENT_AGENT] No vectorstore found: {e}")
        agent_events[-1]["status"] = "error"
        agent_events[-1]["details"] = {"error": str(e)}
        return {
            "status": "error",
            "result": "Aucun document n'a été analysé pour ce projet. Veuillez d'abord uploader des documents.",
            "agent_events": agent_events,
        }
    except Exception as e:
        print(f"[DOCUMENT_AGENT] Error loading vectorstore: {e}")
        agent_events[-1]["status"] = "error"
        agent_events[-1]["details"] = {"error": str(e)}
        return {
            "status": "error",
            "result": f"Erreur lors du chargement du vectorstore: {e}",
            "agent_events": agent_events,
        }

    # Créer un retriever pour rechercher les documents pertinents
    # k=3 signifie qu'on récupère les 3 chunks les plus pertinents
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    print("[DOCUMENT_AGENT] Retriever created with k=3")

    # Émettre l'événement de recherche RAG
    agent_events.append({
        "type": "tool_used",
        "tool_name": "Recherche RAG",
        "tool_icon": "🔍",
        "description": "Recherche des chunks de documents pertinents",
        "status": "running",
    })

    # Récupérer les documents pertinents
    try:
        retrieved_docs = retriever.invoke(user_query)
        print(f"[DOCUMENT_AGENT] Retrieved {len(retrieved_docs)} relevant chunks")
        agent_events[-1]["status"] = "completed"
        agent_events[-1]["details"] = {"chunks_retrieved": len(retrieved_docs)}
    except Exception as e:
        print(f"[DOCUMENT_AGENT] Error retrieving documents: {e}")
        agent_events[-1]["status"] = "error"
        agent_events[-1]["details"] = {"error": str(e)}
        return {
            "status": "error",
            "result": f"Erreur lors de la récupération des documents: {e}",
            "agent_events": agent_events,
        }

    # Formater le contexte récupéré
    context_chunks = []
    for i, doc in enumerate(retrieved_docs, 1):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")
        context_chunks.append(f"[Chunk {i} - Source: {source}, Page: {page}]\n{doc.page_content}")

    context = "\n\n---\n\n".join(context_chunks)
    print(f"[DOCUMENT_AGENT] Context prepared: {len(context)} characters")

    # Charger le contexte du projet (backlog existant)
    storage = ProjectContextService()
    try:
        existing_items = storage.load_context(project_id)
        backlog_summary = f"Backlog actuel avec {len(existing_items)} work items"
        print(f"[DOCUMENT_AGENT] Loaded {len(existing_items)} existing work items")
    except FileNotFoundError:
        existing_items = []
        backlog_summary = "Nouveau projet sans backlog existant"
        print("[DOCUMENT_AGENT] No existing backlog found")

    # Charger le prompt
    prompt_config = load_extract_requirements_prompt()

    # Préparer le prompt utilisateur avec le contexte récupéré
    user_prompt = prompt_config["user_prompt_template"].format(
        context=context,
        query=user_query,
        backlog_summary=backlog_summary,
    )

    # Récupérer le modèle depuis l'environnement
    model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    print(f"[DOCUMENT_AGENT] Using model: {model}")

    # Émettre l'événement d'appel LLM
    agent_events.append({
        "type": "tool_used",
        "tool_name": "Appel LLM",
        "tool_icon": "🧠",
        "description": f"Extraction des exigences avec {model}",
        "status": "running",
        "details": {"model": model},
    })

    try:
        # Appeler le LLM
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": prompt_config["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        # Extraire la réponse
        response_text = response.choices[0].message.content

        print(f"[DOCUMENT_AGENT] LLM response received: {len(response_text)} characters")

        # Mettre à jour le statut
        agent_events[-1]["status"] = "completed"
        agent_events[-1]["details"]["response_length"] = len(response_text)

        # Parser la réponse JSON
        work_items_data = json.loads(response_text)

        if not isinstance(work_items_data, list):
            raise ValueError("LLM response is not a list of work items")

        print(f"[DOCUMENT_AGENT] Extracted {len(work_items_data)} work items")

        # Valider et convertir en WorkItem
        new_items = []
        for item_data in work_items_data:
            # Ajouter le project_id
            item_data["project_id"] = project_id

            # Créer le WorkItem (validation Pydantic)
            work_item = WorkItem(**item_data)
            new_items.append(work_item)

            print(f"[DOCUMENT_AGENT]   - {work_item.type}: {work_item.title}")

        # Construire l'ImpactPlan
        impact_plan = {
            "new_items": [item.model_dump() for item in new_items],
            "modified_items": [],
            "deleted_items": [],
        }

        print("[DOCUMENT_AGENT] ImpactPlan created successfully")
        print(f"[DOCUMENT_AGENT] - {len(new_items)} new items")
        print("[DOCUMENT_AGENT] Workflow paused, awaiting human approval")

        # Émettre l'événement de construction de l'ImpactPlan
        agent_events.append({
            "type": "tool_used",
            "tool_name": "Construction ImpactPlan",
            "tool_icon": "📋",
            "description": "Création du plan d'impact avec les exigences extraites",
            "status": "completed",
            "details": {"new_items_count": len(new_items)},
        })

        return {
            "impact_plan": impact_plan,
            "status": "awaiting_approval",
            "result": f"Extracted {len(new_items)} work items from document",
            "agent_events": agent_events,
        }

    except json.JSONDecodeError as e:
        print(f"[DOCUMENT_AGENT] Error parsing JSON: {e}")
        agent_events[-1]["status"] = "error"
        agent_events[-1]["details"]["error"] = str(e)
        return {
            "status": "error",
            "result": f"Failed to parse LLM response as JSON: {e}",
            "agent_events": agent_events,
        }
    except Exception as e:
        print(f"[DOCUMENT_AGENT] Error: {e}")
        if agent_events and agent_events[-1]["status"] == "running":
            agent_events[-1]["status"] = "error"
            agent_events[-1]["details"]["error"] = str(e)
        return {
            "status": "error",
            "result": f"Failed to extract requirements: {e}",
            "agent_events": agent_events,
        }
