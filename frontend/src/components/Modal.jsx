import {useRef,useEffect,useId} from 'react'
import {X} from 'lucide-react'
export default function Modal({title,children,onClose}){const ref=useRef(null),titleId=useId();useEffect(()=>{const d=ref.current;d.showModal();return()=>d.close()},[]);return <dialog aria-labelledby={titleId} ref={ref} className="modal" onCancel={onClose} onClick={e=>{if(e.target===ref.current)onClose()}}><div className="modal-heading"><h2 id={titleId}>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={20}/></button></div>{children}</dialog>}
