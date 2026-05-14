import React, { useEffect, useState } from 'react';
import Modal from 'react-modal';
import type { ActionItem } from '../types';

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

type Props = {
  jobId: string;
};

type EditForm = {
  title?: string;
  start?: string;
  end?: string;
  participants?: string[];
};

const EventList: React.FC<Props> = ({ jobId }) => {
  const [items, setItems] = useState<ActionItem[]>([]);
  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<ActionItem | null>(null);
  const [form, setForm] = useState<EditForm>({});

  useEffect(() => {
    fetch(`${BASE}/status/${jobId}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.result && data.result.action_items) {
          setItems(data.result.action_items);
        }
      })
      .catch((err) => console.error("Failed to fetch job status", err));
  }, [jobId]);

  const openEdit = (item: ActionItem) => {
    setCurrentItem(item);
    setForm({ title: item.task });
    setModalIsOpen(true);
  };

  const closeModal = () => {
    setModalIsOpen(false);
    setCurrentItem(null);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    if (!currentItem || !currentItem.eventId) return;
    const payload: Record<string, unknown> = {};
    if (form.title) payload.title = form.title;
    if (form.start) payload.start = form.start;
    if (form.end) payload.end = form.end;
    if (form.participants) payload.participants = form.participants;
    try {
      await fetch(`${BASE}/events/${currentItem.eventId}?job_id=${jobId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const res = await fetch(`${BASE}/status/${jobId}`);
      const data = await res.json();
      setItems(data.result.action_items);
      closeModal();
    } catch (err) {
      console.error("Failed to update event", err);
    }
  };

  const handleDelete = async (item: ActionItem) => {
    if (!item.eventId) return;
    try {
      await fetch(`${BASE}/events/${item.eventId}?job_id=${jobId}`, { method: "DELETE" });
      const res = await fetch(`${BASE}/status/${jobId}`);
      const data = await res.json();
      setItems(data.result.action_items);
    } catch (err) {
      console.error("Failed to delete event", err);
    }
  };

  return (
    <div className="event-list">
      <h3 className="text-lg font-bold text-[#0B1633] mb-3">Calendar Events</h3>
      {items.filter((it) => it.eventId).length === 0 ? (
        <p className="text-sm text-[#6B7280]">No calendar events created yet.</p>
      ) : (
        <table className="min-w-full border border-[#E5E7EB] rounded-lg">
          <thead className="bg-[#F8F7F5]">
            <tr>
              <th className="border border-[#E5E7EB] px-3 py-2 text-left text-xs font-bold uppercase text-[#6B7280]">Title</th>
              <th className="border border-[#E5E7EB] px-3 py-2 text-left text-xs font-bold uppercase text-[#6B7280]">Participants</th>
              <th className="border border-[#E5E7EB] px-3 py-2 text-left text-xs font-bold uppercase text-[#6B7280]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.filter((it) => it.eventId).map((it) => (
              <tr key={it.eventId} className="hover:bg-[#F8F7F5]">
                <td className="border border-[#F3F4F6] px-3 py-2 text-sm">{it.task}</td>
                <td className="border border-[#F3F4F6] px-3 py-2 text-sm text-[#6B7280]">{it.context}</td>
                <td className="border border-[#F3F4F6] px-3 py-2">
                  <button onClick={() => openEdit(it)} className="mr-2 text-sm text-[#F26A21] hover:underline">Edit</button>
                  <button onClick={() => handleDelete(it)} className="text-sm text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal isOpen={modalIsOpen} onRequestClose={closeModal} contentLabel="Edit Event" className="bg-white rounded-2xl p-6 max-w-md mx-auto mt-20 shadow-xl border border-[#E5E7EB]" overlayClassName="fixed inset-0 bg-black/40 z-50">
        <h2 className="text-xl font-bold text-[#0B1633] mb-4">Edit Event</h2>
        <label className="block mb-3">
          <span className="text-sm font-medium text-[#5C667A]">Title</span>
          <input name="title" value={form.title || ''} onChange={handleChange} className="mt-1 w-full rounded-xl border border-[#E5E7EB] px-3 py-2 text-sm focus:border-[#F26A21]/50 focus:ring-2 focus:ring-[#F26A21]/10 outline-none" />
        </label>
        <div className="flex gap-3 mt-4">
          <button onClick={handleSubmit} className="px-4 py-2 bg-[#F26A21] text-white rounded-xl text-sm font-bold hover:bg-[#E55D1B]">Save</button>
          <button onClick={closeModal} className="px-4 py-2 border border-[#E5E7EB] rounded-xl text-sm font-medium text-[#5C667A] hover:bg-[#F8F7F5]">Cancel</button>
        </div>
      </Modal>
    </div>
  );
};

export default EventList;
