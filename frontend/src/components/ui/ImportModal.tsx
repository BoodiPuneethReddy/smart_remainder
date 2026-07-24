import React, { useState, useRef, useCallback } from 'react';
import { importApi, ImportPreview, ImportSection, ImportFieldPreview } from '../../lib/api';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: { tasksCreated: number; summary: string }) => void;
  onStartLearning?: (docId: number) => void;
  initialFile?: File | null;
}

type ModalStep = 'upload' | 'preview' | 'approving' | 'done';

const CONFIDENCE_COLORS: Record<string, string> = {
  high: '#10B981',
  medium: '#F59E0B',
  low: '#EF4444',
  not_found: '#98A2B3',
};

const CONFIDENCE_LABELS: Record<string, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low — please verify',
  not_found: 'Not found',
};

function getScoreBadge(pct: number) {
  let color = '#10B981'; // 95-100 green
  if (pct < 60) color = '#EF4444'; // red
  else if (pct < 80) color = '#F59E0B'; // orange
  else if (pct < 95) color = '#3B82F6'; // blue

  return (
    <span
      className="confidence-badge"
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
        fontWeight: 700,
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '0.75rem',
      }}
    >
      {pct}% confidence
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const color = CONFIDENCE_COLORS[confidence] ?? '#3B82F6';
  return (
    <span
      className="confidence-badge"
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
        fontWeight: 600,
        padding: '2px 8px',
        borderRadius: '12px',
        fontSize: '0.75rem',
      }}
    >
      {CONFIDENCE_LABELS[confidence] ?? confidence}
    </span>
  );
}

interface EditableField {
  field_name: string;
  display_label: string;
  value: string;
  confidence: string;
}

export default function ImportModal({ isOpen, onClose, onSuccess, onStartLearning, initialFile }: ImportModalProps) {
  const [step, setStep] = useState<ModalStep>('upload');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [editedFields, setEditedFields] = useState<Record<string, Record<string, string>>>({});
  const [showRawText, setShowRawText] = useState(false);
  const [approveResult, setApproveResult] = useState<{ tasksCreated: number; summary: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (isOpen && initialFile) {
      handleFile(initialFile);
    }
  }, [isOpen, initialFile]);

  const handleFile = useCallback(async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'jpg', 'jpeg', 'png'].includes(ext ?? '')) {
      setUploadError('Only PDF, JPG, and PNG files are supported.');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setUploadError('File too large. Maximum size is 20 MB.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const res = await importApi.upload(file);
      const data = res.data;
      setPreview(data);

      // Initialize editable fields from preview (keyed by unique section index to prevent collisions)
      const initial: Record<string, Record<string, string>> = {};
      data.sections.forEach((section, idx) => {
        const secKey = `${section.document_type}_${idx}`;
        initial[secKey] = {};
        for (const f of section.fields) {
          initial[secKey][f.field_name] = f.value ?? '';
        }
      });
      setEditedFields(initial);
      setStep('preview');
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Document processing failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleApprove = async () => {
    if (!preview) return;
    setStep('approving');
    try {
      const reviewedSections = preview.sections.map((s, idx) => ({
        document_type: s.document_type,
        fields: editedFields[`${s.document_type}_${idx}`] ?? {},
      }));
      const res = await importApi.approve(preview.import_id, reviewedSections);
      const data = (res as any).data;
      const result = {
        tasksCreated: data.tasks_created ?? 0,
        summary: data.ai_summary ?? '',
      };
      setApproveResult(result);
      setStep('done');
      onSuccess?.(result);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Approval failed. Please try again.');
      setStep('preview');
    }
  };

  const reset = () => {
    setStep('upload');
    setPreview(null);
    setEditedFields({});
    setUploadError(null);
    setApproveResult(null);
    setShowRawText(false);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal import-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon">📄</div>
            <div>
              <h2 className="modal-title">Smart Academic Import</h2>
              <p className="modal-subtitle">
                {step === 'upload' && 'Upload your PDF or image — we\'ll extract the academic data'}
                {step === 'preview' && `Reviewing: ${preview?.original_filename}`}
                {step === 'approving' && 'Creating tasks and updating your planner...'}
                {step === 'done' && 'Import successful!'}
              </p>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Upload step */}
          {step === 'upload' && (
            <div>
              <div
                className={`import-dropzone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => !isUploading && fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  style={{ display: 'none' }}
                  onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
                />
                {isUploading ? (
                  <div className="import-dropzone-uploading">
                    <div className="spinner-large" />
                    <p>Analyzing document...</p>
                    <p className="import-hint">Extracting text and classifying academic content</p>
                  </div>
                ) : (
                  <div className="import-dropzone-content">
                    <div className="import-dropzone-icon">📤</div>
                    <p className="import-dropzone-label">Drop your document here or click to browse</p>
                    <p className="import-dropzone-hint">Supported: PDF · JPG · PNG · Max 20 MB</p>
                    <div className="import-capabilities">
                      <span className="cap-item cap-ok">✓ PDF</span>
                      <span className="cap-item cap-ok">✓ Assignment Notices</span>
                      <span className="cap-item cap-ok">✓ Exam Schedules</span>
                      <span className="cap-item cap-ok">✓ Timetables</span>
                    </div>
                  </div>
                )}
              </div>

              {uploadError && (
                <div className="import-error">
                  <span>⚠ {uploadError}</span>
                </div>
              )}
            </div>
          )}

          {/* Preview step */}
          {step === 'preview' && preview && (
            <div className="import-preview">
              {/* Classification header */}
              <div className="import-classification">
                <div className="import-classification-type">
                  <span className="import-type-badge">
                    {preview.document_type === 'mixed_academic'
                      ? 'Mixed Academic Document'
                      : preview.document_type === 'assignment_notice'
                      ? 'Assignment Notice'
                      : preview.document_type === 'exam_schedule'
                      ? 'Exam Schedule'
                      : preview.document_type === 'timetable'
                      ? 'Class Timetable'
                      : preview.document_type === 'unknown_academic'
                      ? 'Academic Document'
                      : preview.document_type.replace('_', ' ')}
                  </span>
                  <span className="import-confidence-bar-wrap">
                    <span
                      className="import-confidence-bar"
                      style={{ width: `${Math.round(preview.classification_confidence * 100)}%` }}
                    />
                  </span>
                  <span className="import-confidence-pct">{Math.round(preview.classification_confidence * 100)}% overall confidence</span>
                </div>
                {preview.ocr_used && <span className="import-ocr-badge">🔍 OCR used</span>}
              </div>

              {/* Categorized Review Sections */}
              {(() => {
                const extractedTasks = preview.sections
                  .map((s, idx) => ({ section: s, idx }))
                  .filter(({ section }) => section.document_type !== 'ignored_item' && section.document_type !== 'needs_confirmation');
                const needsConfirmation = preview.sections
                  .map((s, idx) => ({ section: s, idx }))
                  .filter(({ section }) => section.document_type === 'needs_confirmation');
                const ignoredItems = preview.sections
                  .map((s, idx) => ({ section: s, idx }))
                  .filter(({ section }) => section.document_type === 'ignored_item');

                const renderSectionCard = (section: typeof preview.sections[0], sectionIdx: number, isIgnored = false) => {
                  const secKey = `${section.document_type}_${sectionIdx}`;
                  const isNeedsConf = section.document_type === 'needs_confirmation';
                  
                  // Extract dynamic fields from preview
                  const fieldMap: Record<string, string> = {};
                  section.fields.forEach(f => { fieldMap[f.field_name] = f.value ?? ''; });

                  const priorityStr = fieldMap['priority_preview'] || '50.0 (Medium)';
                  const estHoursStr = fieldMap['estimated_hours'] || '2.0 hrs';
                  const reminderTimingStr = fieldMap['reminder_timing'] || '2 days before';

                  // Compute per-task numerical confidence score dynamically from field confidence
                  const validFields = section.fields.filter(f => !['priority_preview', 'estimated_hours', 'reminder_timing', 'suppressed', 'confirmation_question', 'superseded_date'].includes(f.field_name));
                  let taskScore = 95;
                  if (isIgnored) {
                    taskScore = 20;
                  } else if (isNeedsConf) {
                    taskScore = 41;
                  } else if (validFields.length > 0) {
                    const scoreMap: Record<string, number> = { high: 98, medium: 75, low: 45, not_found: 20 };
                    const total = validFields.reduce((acc, f) => acc + (scoreMap[f.confidence] || 75), 0);
                    taskScore = Math.round(total / validFields.length);
                  }

                  return (
                    <div key={secKey} className={`import-section ${isIgnored ? 'import-section--ignored' : ''}`}>
                      <div className="import-section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <h3 className="import-section-title" style={{ margin: 0 }}>{section.display_name}</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {getScoreBadge(taskScore)}
                        </div>
                      </div>

                      {/* Explainable Confidence Breakdown Drawer */}
                      <details style={{ marginBottom: '10px', fontSize: '0.78rem', color: '#64748B' }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#3B82F6' }}>
                          💡 Why {taskScore}% confidence? (Click to view breakdown)
                        </summary>
                        <div style={{ marginTop: '4px', padding: '6px 10px', background: '#F1F5F9', borderRadius: '6px', fontSize: '0.75rem' }}>
                          <div>✓ Subject: {fieldMap['subject'] || 'Detected'}</div>
                          <div>✓ Title: {section.display_name}</div>
                          {fieldMap['due_date'] || fieldMap['date'] ? (
                            <div>✓ Date parsed ({fieldMap['due_date'] || fieldMap['date']})</div>
                          ) : (
                            <div style={{ color: '#D97706' }}>⚠ Specific date missing</div>
                          )}
                          {fieldMap['faculty'] || fieldMap['instructor'] ? (
                            <div>✓ Instructor linked ({fieldMap['faculty'] || fieldMap['instructor']})</div>
                          ) : null}
                        </div>
                      </details>

                      {/* Candidate Planner Preview Tags */}
                      {!isIgnored && !isNeedsConf && (
                        <div className="import-candidate-preview" style={{ fontSize: '0.8rem', color: 'var(--text-muted, #94A3B8)', marginBottom: '12px', display: 'flex', gap: '12px', flexWrap: 'wrap', background: 'rgba(59, 130, 246, 0.05)', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(59, 130, 246, 0.15)' }}>
                          <span>⚡ Priority: <strong style={{ color: priorityStr.includes('Critical') ? '#EF4444' : priorityStr.includes('High') ? '#F59E0B' : '#3B82F6' }}>{priorityStr}</strong></span>
                          <span>⏱️ Est: <strong>{estHoursStr}</strong></span>
                          <span>🔔 Reminder: <strong>{reminderTimingStr}</strong></span>
                        </div>
                      )}

                      {/* Interactive Needs Confirmation Quick Resolver with Context */}
                      {isNeedsConf && (
                        <div className="import-confirmation-box" style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', padding: '12px', marginBottom: '12px' }}>
                          <p style={{ margin: '0 0 4px 0', fontSize: '0.85rem', fontWeight: 600, color: '#D97706' }}>
                            ⚠️ {fieldMap['confirmation_question'] || `Date unresolved for ${section.display_name}`}
                          </p>
                          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                            <input
                              type="text"
                              className="import-field-input"
                              style={{ fontSize: '0.8rem', padding: '4px 8px', width: '220px' }}
                              value={editedFields[secKey]?.['due_date'] ?? fieldMap['due_date'] ?? ''}
                              onChange={e => {
                                const val = e.target.value;
                                setEditedFields(prev => ({
                                  ...prev,
                                  [secKey]: {
                                    ...prev[secKey],
                                    due_date: val,
                                  },
                                }));
                              }}
                              placeholder="Enter deadline date..."
                            />
                          </div>
                        </div>
                      )}

                      {/* Friendly Ignored Item Explanation */}
                      {isIgnored && (
                        <div className="import-ignored-explanation" style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px', padding: '10px 12px', marginBottom: '12px', fontSize: '0.85rem', color: '#DC2626' }}>
                          🚫 <strong>Ignored automatically:</strong> {fieldMap['suppressed'] || 'Document requested not to create tasks for this item. No reminder will be created.'}
                        </div>
                      )}

                      {section.possible_duplicates.length > 0 && (
                        <div className="import-duplicate-warning">
                          ⚠ Possible duplicate found: {section.possible_duplicates[0].title}
                        </div>
                      )}

                      {section.missing_required.length > 0 && (
                        <div className="import-missing-warning">
                          ⚠ Required fields missing: {section.missing_required.join(', ')} — please fill in below
                        </div>
                      )}

                      <div className="import-fields">
                        {section.fields.filter(f => !['priority_preview', 'estimated_hours', 'reminder_timing', 'suppressed', 'confirmation_question', 'superseded_date'].includes(f.field_name)).map(field => (
                          <div key={field.field_name} className={`import-field ${field.confidence === 'not_found' ? 'import-field--empty' : ''}`}>
                            <div className="import-field-header">
                              <label className="import-field-label">{field.display_label}</label>
                              <ConfidenceBadge confidence={field.confidence} />
                            </div>
                            <input
                              type="text"
                              className="import-field-input"
                              disabled={isIgnored}
                              value={editedFields[secKey]?.[field.field_name] ?? ''}
                              onChange={e => {
                                const val = e.target.value;
                                setEditedFields(prev => ({
                                  ...prev,
                                  [secKey]: {
                                    ...prev[secKey],
                                    [field.field_name]: val,
                                  },
                                }));
                              }}
                              placeholder={field.confidence === 'not_found' ? 'Not detected — enter manually' : ''}
                            />
                          </div>
                        ))}
                      </div>

                      {/* Interactive Source Highlighting Snippet Drawer */}
                      <details style={{ marginTop: '10px', fontSize: '0.8rem', color: '#64748B' }}>
                        <summary style={{ cursor: 'pointer', fontWeight: 600, userSelect: 'none' }}>
                          🔍 View Source Text Snippet
                        </summary>
                        <div style={{ marginTop: '6px', padding: '8px 12px', background: '#F8FAFC', borderRadius: '6px', borderLeft: '3px solid #3B82F6', fontFamily: 'monospace', fontSize: '0.78rem' }}>
                          Source grounding: <mark style={{ background: '#FDE047', padding: '2px 4px', borderRadius: '4px', fontWeight: 600 }}>{section.display_name}</mark>
                        </div>
                      </details>
                    </div>
                  );
                };

                return (
                  <div className="import-categorized-groups">
                    {/* Panel 1: Extracted Tasks */}
                    {extractedTasks.length > 0 && (
                      <div className="import-group-panel">
                        <h4 className="import-group-title import-group-title--tasks">📋 Extracted Tasks ({extractedTasks.length})</h4>
                        {extractedTasks.map(({ section, idx }) => renderSectionCard(section, idx))}
                      </div>
                    )}

                    {/* Panel 2: Needs Confirmation */}
                    {needsConfirmation.length > 0 && (
                      <div className="import-group-panel">
                        <h4 className="import-group-title import-group-title--confirmation">⚠️ Needs Confirmation ({needsConfirmation.length})</h4>
                        {needsConfirmation.map(({ section, idx }) => renderSectionCard(section, idx))}
                      </div>
                    )}

                    {/* Panel 3: Ignored Items */}
                    {ignoredItems.length > 0 && (
                      <div className="import-group-panel">
                        <h4 className="import-group-title import-group-title--ignored">🚫 Ignored Items ({ignoredItems.length}) — Will NOT create tasks</h4>
                        {ignoredItems.map(({ section, idx }) => renderSectionCard(section, idx, true))}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Raw text transparency */}
              <div className="import-transparency">
                <button
                  className="btn-ghost btn-sm"
                  onClick={() => setShowRawText(s => !s)}
                >
                  {showRawText ? '▲ Hide' : '▼ View'} extracted text (transparency)
                </button>
                {showRawText && (
                  <pre className="import-raw-text">{preview.extracted_text_snippet}
                    {preview.extracted_text_snippet.length >= 300 && '\n[...truncated. Full text in original document.]'}
                  </pre>
                )}
              </div>

              {uploadError && <div className="import-error"><span>⚠ {uploadError}</span></div>}
            </div>
          )}

          {/* Approving */}
          {step === 'approving' && (
            <div className="import-approving">
              <div className="spinner-large" />
              <p>Creating tasks in your planner...</p>
              <p className="import-hint">Calculating priorities · Scheduling reminders · Generating AI summary</p>
            </div>
          )}

          {/* Done */}
          {step === 'done' && approveResult && (
            <div className="import-done">
              <div className="import-done-icon">✓</div>
              <h3>{approveResult.tasksCreated} task{approveResult.tasksCreated !== 1 ? 's' : ''} created</h3>
              <div className="import-ai-summary">
                <p className="import-ai-label">🤖 AI Study Recommendation</p>
                <p>{approveResult.summary}</p>
              </div>
            </div>
          )}
        </div>

        {/* Pre-Submission Summary Bar */}
        {step === 'preview' && preview && (
          <div className="import-presubmission-summary" style={{ background: '#F1F5F9', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0', padding: '10px 20px', fontSize: '0.82rem', color: '#334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              Will create: <strong style={{ color: '#059669' }}>{preview.sections.filter(s => s.document_type !== 'ignored_item').length} Tasks</strong> · <span style={{ color: '#D97706' }}>{preview.sections.filter(s => s.document_type === 'needs_confirmation').length} Pending Confirmation</span> · <span style={{ color: '#DC2626' }}>{preview.sections.filter(s => s.document_type === 'ignored_item').length} Ignored</span>
            </div>
            <div>
              Total Est. Study: <strong>{(() => {
                const totalHours = preview.sections
                  .filter(s => s.document_type !== 'ignored_item')
                  .reduce((acc, s) => {
                    const fieldMap: Record<string, string> = {};
                    s.fields.forEach(f => { fieldMap[f.field_name] = f.value ?? ''; });
                    const hrsStr = fieldMap['estimated_hours'] || '2.0';
                    const hrs = parseFloat(hrsStr.replace(/[^0-9.]/g, '')) || 2.0;
                    return acc + hrs;
                  }, 0);
                return `${totalHours.toFixed(1)} hours`;
              })()}</strong>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="modal-footer">
          {step === 'upload' && (
            <button className="btn-ghost" onClick={onClose}>Cancel</button>
          )}

          {step === 'preview' && (
            <>
              <button className="btn-ghost" onClick={reset}>← Try another file</button>
              {preview?.import_id && (
                <a
                  href={importApi.viewSource(preview.import_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-ghost btn-sm"
                >
                  🔍 View Source
                </a>
              )}
              <button className="btn-primary" onClick={handleApprove}>
                ✓ Create Tasks
              </button>
            </>
          )}

          {step === 'done' && (
            <>
              <button className="btn-ghost" onClick={reset}>Import another</button>
              <button
                className="btn-primary"
                style={{ backgroundColor: '#2563EB', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={() => {
                  if (preview?.import_id && onStartLearning) {
                    onStartLearning(preview.import_id);
                  }
                  onClose();
                }}
              >
                <span>🚀 Start AI Learning Session</span>
              </button>
              <button className="btn-secondary" onClick={onClose}>Close</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
