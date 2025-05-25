import React, { useState } from 'react';
import { marked } from 'marked';
import mermaid from 'mermaid';

// Initialize mermaid
mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
});

// Helper to recursively render objects/arrays as lists
function renderObject(obj) {
    if (Array.isArray(obj)) {
        return (
            <ul style={{ marginLeft: 16 }}>
                {obj.map((item, idx) => (
                    <li key={idx}>{renderObject(item)}</li>
                ))}
            </ul>
        );
    } else if (typeof obj === 'object' && obj !== null) {
        return (
            <ul style={{ marginLeft: 16 }}>
                {Object.entries(obj).map(([key, value]) => (
                    <li key={key}>
                        <strong>{key}:</strong> {renderObject(value)}
                    </li>
                ))}
            </ul>
        );
    } else {
        return String(obj);
    }
}

const AnalysisReport = ({ report }) => {
    const [expandedSections, setExpandedSections] = useState({});

    const toggleSection = (sectionId) => {
        setExpandedSections(prev => ({
            ...prev,
            [sectionId]: !prev[sectionId]
        }));
    };

    const renderMarkdown = (markdown) => {
        // Process mermaid diagrams before rendering markdown
        const processedMarkdown = markdown.replace(
            /```mermaid\n([\s\S]*?)\n```/g,
            (match, diagram) => {
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                setTimeout(() => {
                    mermaid.render(id, diagram).then(({ svg }) => {
                        const element = document.getElementById(id);
                        if (element) {
                            element.innerHTML = svg;
                        }
                    });
                }, 0);
                return `<div id="${id}" class="mermaid-diagram"></div>`;
            }
        );

        return { __html: marked(processedMarkdown) };
    };

    return (
        <div className="space-y-6">
            {/* Project Summary */}
            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-4">Project Summary</h2>
                <p className="text-gray-700">{report.project_summary}</p>
                <div className="mt-4">
                    <h3 className="text-lg font-semibold mb-2">Tech Stack</h3>
                    <div className="flex flex-wrap gap-2">
                        {report.detected_tech_stack.map((tech, index) => (
                            <span
                                key={index}
                                className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                            >
                                {tech}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Perspectives */}
            <div className="space-y-4">
                {Object.entries(report.perspectives).map(([name, perspective], index) => (
                    <div key={index} className="bg-white rounded-lg shadow">
                        <button
                            className="w-full text-left px-6 py-4 flex justify-between items-center"
                            onClick={() => toggleSection(name)}
                        >
                            <h3 className="text-xl font-semibold">{name}</h3>
                            <span className="text-gray-500">
                                {expandedSections[name] ? '▼' : '▶'}
                            </span>
                        </button>
                        {expandedSections[name] && (
                            <div className="px-6 py-4 border-t">
                                {/* Render structured fields if present, else fallback to markdown */}
                                {perspective.api_endpoints ? (
                                    <div>
                                        <h4 className="font-bold text-blue-700 mb-2">API Endpoints</h4>
                                        {renderObject(perspective.api_endpoints)}
                                    </div>
                                ) : null}
                                {perspective.key_ui_components ? (
                                    <div>
                                        <h4 className="font-bold text-blue-700 mb-2">Key UI Components</h4>
                                        {renderObject(perspective.key_ui_components)}
                                    </div>
                                ) : null}
                                {perspective.data_models ? (
                                    <div>
                                        <h4 className="font-bold text-blue-700 mb-2">Data Models</h4>
                                        {renderObject(perspective.data_models)}
                                    </div>
                                ) : null}
                                {/* Fallback to markdown if no structured fields */}
                                {perspective.raw_markdown && (
                                    <div
                                        className="prose max-w-none"
                                        dangerouslySetInnerHTML={renderMarkdown(perspective.raw_markdown)}
                                    />
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default AnalysisReport; 