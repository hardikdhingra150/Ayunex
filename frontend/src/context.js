import { createContext, useContext } from 'react'
export const AppContext=createContext(null)
export function useApp(){return useContext(AppContext)}
export const initialCases=[
 {id:'ni-001',title:'Ashwagandha formulation',sample:true,status:'Needs information',jurisdiction:'IN',asOf:'2026-09-10',facts:{name:'Ashwagandha formulation',use:'Therapeutic',form:'Capsule',ingredients:'Ashwagandha',origin:'Unknown',source:'Unknown'},confirmed:false,completed:[],versions:[]},
 {id:'ni-002',title:'Botanical skincare concept',sample:true,status:'Draft',jurisdiction:'IN',asOf:'2026-09-10',facts:{name:'Botanical skincare concept',use:'Cosmetic',form:'Topical',ingredients:'Unknown'},confirmed:false,completed:[],versions:[]}
]
export function makeCase(title,jurisdiction='IN'){return {id:`ni-${crypto.randomUUID().slice(0,8)}`,title,sample:false,status:'Draft',jurisdiction,asOf:new Date().toISOString().slice(0,10),facts:{name:title},confirmed:false,completed:[],versions:[]}}
