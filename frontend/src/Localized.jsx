import { cloneElement, isValidElement, Children } from 'react'
import { useApp } from './context'
import { uiHindi } from './uiHindi'

// Translate declared UI copy, not DOM nodes, case values or official evidence.
export default function Localized({children}){
 const {language}=useApp()
 function text(value){if(language!=='hi'||typeof value!=='string')return value;const key=value.trim();return uiHindi[key]?value.replace(key,uiHindi[key]):value}
 function visit(node){
  if(typeof node==='string')return text(node)
  if(!isValidElement(node)||node.props['data-original'])return node
  const props={}
  for(const key of ['title','body','placeholder','aria-label'])if(typeof node.props[key]==='string'&&!(key==='title'&&node.props.originalTitle))props[key]=text(node.props[key])
  if(node.type==='option'&&node.props.value===undefined)props.value=typeof node.props.children==='string'?node.props.children:undefined
  if(node.props.children!==undefined)props.children=Children.map(node.props.children,visit)
  return cloneElement(node,props)
 }
 return Children.map(children,visit)
}
