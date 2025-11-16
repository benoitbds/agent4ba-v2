"use client";

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface MermaidDiagramProps {
  code: string;
}

/**
 * Extrait le code Mermaid pur en retirant les balises markdown
 * @param rawCode - Code qui peut contenir des balises markdown ```mermaid ... ```
 * @returns Code Mermaid nettoyé
 */
function extractMermaidCode(rawCode: string): string {
  // Supprimer les balises markdown si présentes (```mermaid ou juste ```)
  const match = rawCode.match(/```(?:mermaid)?\s*([\s\S]*?)```/);
  if (match) {
    return match[1].trim();
  }
  // Si pas de balises, retourner le code tel quel (déjà nettoyé)
  return rawCode.trim();
}

/**
 * Extrait le numéro de ligne d'un message d'erreur Mermaid
 * @param errorMessage - Message d'erreur de Mermaid
 * @returns Numéro de ligne ou null si non trouvé
 */
function extractLineNumber(errorMessage: string): number | null {
  // Chercher des patterns comme "line 7", "on line 5", "in line 3", etc.
  const lineMatch = errorMessage.match(/(?:line|Line)\s+(\d+)/);
  if (lineMatch) {
    return parseInt(lineMatch[1], 10);
  }
  return null;
}

/**
 * Composant pour afficher un diagramme Mermaid avec gestion d'erreur non bloquante
 *
 * @param code - Code Mermaid à rendre
 */
export default function MermaidDiagram({ code }: MermaidDiagramProps) {
  const t = useTranslations();
  const containerRef = useRef<HTMLDivElement>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    // Initialiser Mermaid avec la configuration
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'monospace',
    });

    const renderDiagram = async () => {
      if (!containerRef.current) return;

      try {
        // 1. Nettoyer le code en retirant les balises markdown
        const cleanCode = extractMermaidCode(code);

        // 2. Vérifier que le code n'est pas vide après nettoyage
        if (!cleanCode) {
          setParseError('Le code Mermaid est vide');
          return;
        }

        // 3. Générer un ID unique pour le diagramme
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // 4. Rendre le diagramme avec le code NETTOYÉ
        const { svg } = await mermaid.render(id, cleanCode);

        // 5. Insérer le SVG dans le conteneur
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }

        // 6. Réinitialiser l'erreur si le rendu réussit
        setParseError(null);
      } catch (err) {
        console.error('Error rendering Mermaid diagram:', err);
        // Ne pas effacer le conteneur - garder le dernier SVG valide
        // Juste définir l'erreur pour afficher une bannière discrète
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';

        // Extraire le numéro de ligne si possible
        const lineNumber = extractLineNumber(errorMessage);

        // Créer un message d'erreur simplifié et traduit
        const simplifiedError = lineNumber
          ? t('diagram.editor.parseErrorWithLine', { line: lineNumber })
          : t('diagram.editor.parseError');

        setParseError(simplifiedError);
      }
    };

    renderDiagram();
  }, [code]);

  return (
    <div className="relative w-full">
      {/* Conteneur du diagramme - conserve toujours sa taille */}
      <div
        ref={containerRef}
        className="mermaid-diagram bg-white border border-gray-200 rounded p-4 overflow-x-auto"
        style={{ minHeight: '100px' }}
      />

      {/* Bannière d'erreur discrète - affichée uniquement si erreur */}
      {parseError && (
        <div className="absolute bottom-0 left-0 right-0 mx-4 mb-4 bg-red-50 border border-red-300 rounded-lg shadow-md animate-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-start gap-2 p-3">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-red-700 break-words">
                {parseError}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
