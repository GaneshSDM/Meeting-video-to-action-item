import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Modal from 'react-modal';
import type { ActionItem } from '../types';

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
    // Fetch job status to get action items
    axios.get(`/status/${jobId}`).then((res) => {
      const data = res.data;
      if (data.result && data.result.action_items) {
        setItems(data.result.action_items);
      }
    });
  }, [jobId]);

  const openEdit = (item: ActionItem) => {
    setCurrentItem(item);
    setForm({
      title: item.task,
      // start/end placeholders – actual values would come from event data if stored
    });
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
    const payload: any = {};
    if (form.title) payload.title = form.title;
    if (form.start) payload.start = form.start;
    if (form.end) payload.end = form.end;
    if (form.participants) payload.participants = form.participants;
    await axios.patch(`/events/${currentItem.eventId}?job_id=${jobId}`, payload);
    // Refresh list after update
    const res = await axios.get(`/status/${jobId}`);
    setItems(res.data.result.action_items);
    closeModal();
  };

  const handleDelete = async (item: ActionItem) => {
    if (!item.eventId) return;
    await axios.delete(`/events/${item.eventId}?job_id=${jobId}`);
    const res = await axios.get(`/status/${jobId}`);
    setItems(res.data.result.action_items);
  };

  return (
    <div className="event-list">
      <h3>Calendar Events</h3>
      <table className="min-w-full border">
        <thead>
          <tr>
            <th className="border px-2">Title</th>
            <th className="border px-2">Participants</th>
            <th className="border px-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.eventId}>
              <td className="border px-2">{it.task}</td>
              <td className="border px-2">{it.context}</td>
              <td className="border px-2">
                <button onClick={() => openEdit(it)} className="mr-2">Edit</button>
                <button onClick={() => handleDelete(it)} className="text-red-600">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Modal isOpen={modalIsOpen} onRequestClose={closeModal} contentLabel="Edit Event">
        <h2>Edit Event</h2>
        <label>
          Title:
          <input name="title" value={form.title || ''} onChange={handleChange} />
        </label>
        {/* Additional fields for start, end, participants can be added */}
        <button onClick={handleSubmit}>Save</button>
        <button onClick={closeModal}>Cancel</button>
      </Modal>
    </div>
  );
};

export default EventList;
